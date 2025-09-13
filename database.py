import sqlite3
import hashlib
import datetime

class Database:
    """Handles all database operations for the ticketing system."""
    def __init__(self, db_name="ticketing_system.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self._update_schema() # Check and update schema on startup
        self.create_admin_if_not_exists()

    def _update_schema(self):
        """Checks and updates the database schema to include new columns."""
        try:
            # Check if 'resolved_at' column exists in 'tickets' table
            self.cursor.execute("PRAGMA table_info(tickets)")
            columns = [info[1] for info in self.cursor.fetchall()]
            if 'resolved_at' not in columns:
                self.cursor.execute("ALTER TABLE tickets ADD COLUMN resolved_at TIMESTAMP")
                self.conn.commit()
                print("Database schema updated: Added 'resolved_at' column to tickets table.")
        except Exception as e:
            # This might fail if the tickets table doesn't exist yet, which is fine.
            pass

    def create_tables(self):
        """Creates the necessary tables if they don't already exist."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'agent', 'requester'))
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Open', 'In Progress', 'Resolved')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                requester_id INTEGER NOT NULL,
                agent_id INTEGER,
                FOREIGN KEY (requester_id) REFERENCES users (id),
                FOREIGN KEY (agent_id) REFERENCES users (id)
            )
        ''')
        self.conn.commit()

    def create_admin_if_not_exists(self):
        """Creates a default admin user if one doesn't exist."""
        self.cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not self.cursor.fetchone():
            hashed_password = self._hash_password('admin')
            self.cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ('admin', hashed_password, 'admin')
            )
            self.conn.commit()

    def _hash_password(self, password):
        """Hashes a password for secure storage."""
        return hashlib.sha256(password.encode()).hexdigest()

    def check_credentials(self, username, password):
        """Verifies user credentials and returns user data if valid."""
        hashed_password = self._hash_password(password)
        self.cursor.execute(
            "SELECT id, username, role FROM users WHERE username = ? AND password = ?",
            (username, hashed_password)
        )
        return self.cursor.fetchone()

    def register_user(self, username, password, role='requester'):
        """Registers a new user (requester or agent)."""
        if role not in ['requester', 'agent']:
            return False, "Invalid role specified."
        try:
            hashed_password = self._hash_password(password)
            self.cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, hashed_password, role)
            )
            self.conn.commit()
            return True, "User registered successfully."
        except sqlite3.IntegrityError:
            return False, "Username already exists."
        except Exception as e:
            return False, f"An error occurred: {e}"

    def get_users_by_role(self, role):
        """Fetches all users with a specific role."""
        self.cursor.execute("SELECT id, username FROM users WHERE role = ?", (role,))
        return self.cursor.fetchall()

    def count_users(self):
        """Counts the number of users for each role."""
        self.cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
        return dict(self.cursor.fetchall())

    def create_ticket(self, title, description, requester_id):
        """Creates a new ticket."""
        self.cursor.execute(
            "INSERT INTO tickets (title, description, status, requester_id) VALUES (?, ?, ?, ?)",
            (title, description, 'Open', requester_id)
        )
        self.conn.commit()

    def get_all_tickets(self):
        """Retrieves all tickets with user details for the admin view."""
        query = """
            SELECT
                t.id, t.title, t.status,
                req.username as requester,
                COALESCE(ag.username, 'Not Assigned') as agent,
                t.created_at
            FROM tickets t
            JOIN users req ON t.requester_id = req.id
            LEFT JOIN users ag ON t.agent_id = ag.id
            ORDER BY t.created_at DESC
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_agent_tickets(self, agent_id):
        """Retrieves tickets assigned to a specific agent."""
        query = """
            SELECT
                t.id, t.title, t.status, req.username as requester, t.created_at
            FROM tickets t
            JOIN users req ON t.requester_id = req.id
            WHERE t.agent_id = ?
            ORDER BY t.created_at DESC
        """
        self.cursor.execute(query, (agent_id,))
        return self.cursor.fetchall()

    def get_requester_tickets(self, requester_id):
        """Retrieves tickets created by a specific requester."""
        query = """
            SELECT
                t.id, t.title, t.status, COALESCE(ag.username, 'Not Assigned') as agent, t.created_at
            FROM tickets t
            LEFT JOIN users ag ON t.agent_id = ag.id
            WHERE t.requester_id = ?
            ORDER BY t.created_at DESC
        """
        self.cursor.execute(query, (requester_id,))
        return self.cursor.fetchall()
        
    def get_ticket_details(self, ticket_id):
        """Retrieves full details for a single ticket."""
        query = """
            SELECT
                t.id, t.title, t.description, t.status,
                req.username as requester,
                COALESCE(ag.username, 'Not Assigned') as agent,
                t.created_at,
                t.updated_at,
                t.resolved_at
            FROM tickets t
            JOIN users req ON t.requester_id = req.id
            LEFT JOIN users ag ON t.agent_id = ag.id
            WHERE t.id = ?
        """
        self.cursor.execute(query, (ticket_id,))
        return self.cursor.fetchone()

    def assign_ticket(self, ticket_id, agent_id):
        """Assigns a ticket to an agent."""
        self.cursor.execute(
            "UPDATE tickets SET agent_id = ?, updated_at = ? WHERE id = ?",
            (agent_id, datetime.datetime.now(), ticket_id)
        )
        self.conn.commit()

    def update_ticket_status(self, ticket_id, new_status):
        """Updates the status of a ticket."""
        now = datetime.datetime.now()
        
        # Base query and parameters
        sql = "UPDATE tickets SET status = ?, updated_at = ? "
        params = [new_status, now]

        # Handle the 'resolved_at' field specifically
        if new_status == 'Resolved':
            # Add the resolved timestamp to the query
            sql += ", resolved_at = ? "
            params.append(now)
        else:
            # Explicitly set resolved_at to NULL if status is anything other than Resolved
            sql += ", resolved_at = NULL "

        # Add the WHERE clause to target the correct ticket
        sql += "WHERE id = ?"
        params.append(ticket_id)

        # Execute the constructed query and commit the changes
        self.cursor.execute(sql, tuple(params))
        self.conn.commit()
        
    def get_weekly_report(self):
        """Generates a report of tickets closed in the last 7 days."""
        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        query = """
            SELECT
                t.id, t.title, ag.username as agent, t.updated_at
            FROM tickets t
            JOIN users ag ON t.agent_id = ag.id
            WHERE t.status = 'Resolved' AND t.updated_at >= ?
            ORDER BY t.updated_at DESC
        """
        self.cursor.execute(query, (seven_days_ago,))
        return self.cursor.fetchall()

    def get_agent_performance_report(self):
        """
        Calculates performance metrics for each agent.
        Returns: A list of tuples with (agent_name, assigned_count, resolved_count, avg_resolution_days).
        """
        query = """
            SELECT
                u.username,
                COUNT(t.id) as assigned_tickets,
                SUM(CASE WHEN t.status = 'Resolved' THEN 1 ELSE 0 END) as resolved_tickets,
                AVG(CASE WHEN t.status = 'Resolved' THEN JULIANDAY(t.resolved_at) - JULIANDAY(t.created_at) ELSE NULL END) as avg_resolution_days
            FROM
                users u
            LEFT JOIN
                tickets t ON u.id = t.agent_id
            WHERE
                u.role = 'agent'
            GROUP BY
                u.id, u.username
            ORDER BY
                resolved_tickets DESC
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

