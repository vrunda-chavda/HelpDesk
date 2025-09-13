import tkinter as tk
from tkinter import ttk, messagebox
from database import Database
from datetime import datetime
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    
# Use ttkbootstrap for modern themes and widgets
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

def format_timedelta(start_time_str, end_time_str):
    """Formats the duration between two ISO format time strings."""
    if not start_time_str or not end_time_str:
        return "N/A"
    
    # Handle potential timezone info if present, but SQLite format is usually without it
    start_time_str = start_time_str.split('+')[0]
    end_time_str = end_time_str.split('+')[0]
    
    # SQLite can have a space or a 'T' separator
    start_time_str = start_time_str.replace('T', ' ')
    end_time_str = end_time_str.replace('T', ' ')
    
    try:
        # Accommodate formats with or without milliseconds
        fmt = "%Y-%m-%d %H:%M:%S.%f"
        start_time = datetime.strptime(start_time_str, fmt)
    except ValueError:
        fmt = "%Y-%m-%d %H:%M:%S"
        start_time = datetime.strptime(start_time_str, fmt)
        
    try:
        fmt = "%Y-%m-%d %H:%M:%S.%f"
        end_time = datetime.strptime(end_time_str, fmt)
    except ValueError:
        fmt = "%Y-%m-%d %H:%M:%S"
        end_time = datetime.strptime(end_time_str, fmt)

    duration = end_time - start_time
    
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    # Only show seconds if the duration is less than a minute
    if not parts or (days == 0 and hours == 0 and minutes == 0):
        parts.append(f"{seconds}s")
        
    return " ".join(parts)


# --- GUI APPLICATION ---
class TicketingApp(tb.Window): # Use tb.Window for themes
    """Main application class that manages frames and user session."""
    def __init__(self, db):
        # Change the theme name here.
        # Examples: "superhero", "darkly", "cosmo", "flatly", "journal", "lumen", "minty", "pulse", "sandstone", "united", "yeti"
        super().__init__(themename="yeti") 
        self.db = db
        self.title("IT Help Desk Ticketing System")
        self.geometry("900x600")
        
        # The 'style' object is automatically created and attached to the Window
        self.style.configure('TFrame', background=self.style.lookup('TFrame', 'background'))
        self.style.configure('TLabel', font=('Arial', 12))
        self.style.configure('TButton', font=('Arial', 12))
        self.style.configure('TEntry', font=('Arial', 12))

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        self.current_user = None

        for F in (LoginFrame, RegisterFrame):
            frame = F(self.container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("LoginFrame")

    def show_frame(self, page_name):
        """Brings the specified frame to the front."""
        frame = self.frames[page_name]
        frame.tkraise()

    def login_success(self, user_data):
        """Handles successful login and navigates to the correct dashboard."""
        self.current_user = {'id': user_data[0], 'username': user_data[1], 'role': user_data[2]}
        
        dashboard_class = None
        if self.current_user['role'] == 'admin':
            dashboard_class = AdminDashboard
        elif self.current_user['role'] == 'agent':
            dashboard_class = AgentDashboard
        elif self.current_user['role'] == 'requester':
            dashboard_class = RequesterDashboard

        if dashboard_class:
            # Destroy old dashboards if they exist to refresh data
            if 'AdminDashboard' in self.frames: self.frames['AdminDashboard'].destroy()
            if 'AgentDashboard' in self.frames: self.frames['AgentDashboard'].destroy()
            if 'RequesterDashboard' in self.frames: self.frames['RequesterDashboard'].destroy()

            frame = dashboard_class(self.container, self)
            self.frames[dashboard_class.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            self.show_frame(dashboard_class.__name__)

    def logout(self):
        """Logs out the current user and returns to the login screen."""
        self.current_user = None
        self.show_frame("LoginFrame")


class LoginFrame(ttk.Frame):
    """Login screen for all users."""
    def __init__(self, parent, controller):
        super().__init__(parent, padding="20")
        self.controller = controller

        tb.Label(self, text="Login", font=("Arial", 24, "bold"), bootstyle="primary").pack(pady=20)
        
        form_frame = ttk.Frame(self)
        form_frame.pack(pady=10)

        tb.Label(form_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.username_entry = tb.Entry(form_frame, width=30)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)
        
        tb.Label(form_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.password_entry = tb.Entry(form_frame, show="*", width=30)
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)
        
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)
        
        tb.Button(button_frame, text="Login", command=self.login, bootstyle="success").pack(side="left", padx=10)
        tb.Button(button_frame, text="Register as Requester", command=lambda: controller.show_frame("RegisterFrame"), bootstyle="secondary").pack(side="left", padx=10)
        
    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            Messagebox.show_error("Username and password cannot be empty.", "Error")
            return

        user_data = self.controller.db.check_credentials(username, password)
        if user_data:
            self.username_entry.delete(0, 'end')
            self.password_entry.delete(0, 'end')
            self.controller.login_success(user_data)
        else:
            Messagebox.show_error("Invalid username or password.", "Login Failed")

class RegisterFrame(ttk.Frame):
    """Registration screen for new requesters."""
    def __init__(self, parent, controller):
        super().__init__(parent, padding="20")
        self.controller = controller

        tb.Label(self, text="Register New Requester", font=("Arial", 24, "bold"), bootstyle="primary").pack(pady=20)
        
        form_frame = ttk.Frame(self)
        form_frame.pack(pady=10)

        tb.Label(form_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.username_entry = tb.Entry(form_frame, width=30)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)
        
        tb.Label(form_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.password_entry = tb.Entry(form_frame, show="*", width=30)
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)
        
        tb.Label(form_frame, text="Confirm Password:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.confirm_password_entry = tb.Entry(form_frame, show="*", width=30)
        self.confirm_password_entry.grid(row=2, column=1, padx=5, pady=5)
        
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)

        tb.Button(button_frame, text="Register", command=self.register, bootstyle="success").pack(side="left", padx=10)
        tb.Button(button_frame, text="Back to Login", command=lambda: controller.show_frame("LoginFrame"), bootstyle="secondary").pack(side="left", padx=10)

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()

        if not username or not password or not confirm_password:
            Messagebox.show_error("All fields are required.", "Error")
            return
        if password != confirm_password:
            Messagebox.show_error("Passwords do not match.", "Error")
            return
            
        success, message = self.controller.db.register_user(username, password, 'requester')
        if success:
            Messagebox.show_info(message, "Success")
            self.controller.show_frame("LoginFrame")
        else:
            Messagebox.show_error(message, "Registration Failed")

# --- DASHBOARDS ---

class AdminDashboard(ttk.Frame):
    """Admin dashboard with multiple tabs for managing the system."""
    def __init__(self, parent, controller):
        super().__init__(parent, padding="10")
        self.controller = controller
        
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', pady=5)
        
        tb.Label(header_frame, text=f"Admin Dashboard - Welcome, {self.controller.current_user['username']}!", font=("Arial", 16), bootstyle="primary").pack(side="left")
        tb.Button(header_frame, text="Logout", command=controller.logout, bootstyle="danger").pack(side="right")
        
        self.notebook = tb.Notebook(self)
        self.notebook.pack(expand=True, fill="both", pady=10)
        
        # Tabs
        self.tickets_tab = tb.Frame(self.notebook, padding="10")
        self.users_tab = tb.Frame(self.notebook, padding="10")
        self.reports_tab = tb.Frame(self.notebook, padding="10")
        self.performance_tab = tb.Frame(self.notebook, padding="10")
        
        self.notebook.add(self.tickets_tab, text="All Tickets")
        self.notebook.add(self.users_tab, text="Manage Users")
        self.notebook.add(self.reports_tab, text="Reports")
        self.notebook.add(self.performance_tab, text="Performance")

        self.populate_tickets_tab()
        self.populate_users_tab()
        self.populate_reports_tab()
        self.populate_performance_tab()

    def populate_tickets_tab(self):
        """Create and fill the 'All Tickets' tab."""
        # Treeview for displaying tickets
        columns = ("id", "title", "status", "requester", "agent", "created_at")
        self.tickets_tree = tb.Treeview(self.tickets_tab, columns=columns, show="headings", bootstyle="primary")
        for col in columns:
            self.tickets_tree.heading(col, text=col.replace('_', ' ').title())
            self.tickets_tree.column(col, width=100)
        self.tickets_tree.pack(expand=True, fill="both")
        self.refresh_tickets_list()

        # Action buttons
        action_frame = tb.Frame(self.tickets_tab, padding="10")
        action_frame.pack(fill="x")
        
        tb.Button(action_frame, text="View Details", command=self.view_ticket_details, bootstyle="info").pack(side="left", padx=5)
        tb.Button(action_frame, text="Assign Ticket", command=self.assign_ticket_window, bootstyle="success").pack(side="left", padx=5)
        tb.Button(action_frame, text="Refresh List", command=self.refresh_tickets_list, bootstyle="secondary").pack(side="left", padx=5)

    def refresh_tickets_list(self):
        """Clears and re-populates the tickets treeview."""
        for item in self.tickets_tree.get_children():
            self.tickets_tree.delete(item)
        for ticket in self.controller.db.get_all_tickets():
            self.tickets_tree.insert("", "end", values=ticket)

    def view_ticket_details(self, event=None):
        """Shows a popup with full ticket details."""
        selected_item = self.tickets_tree.focus()
        if not selected_item:
            Messagebox.show_warning("Please select a ticket to view.", "No Selection")
            return
        ticket_id = int(self.tickets_tree.item(selected_item)['values'][0])
        details = self.controller.db.get_ticket_details(ticket_id)
        if details:
            details_str = (
                f"ID: {details[0]}\n"
                f"Title: {details[1]}\n"
                f"Description: {details[2]}\n"
                f"Status: {details[3]}\n"
                f"Requester: {details[4]}\n"
                f"Agent: {details[5]}\n"
                f"Created At: {details[6]}\n"
                f"Last Updated: {details[7] or 'N/A'}\n"
            )
            
            if details[8]: # resolved_at is not null
                resolution_time = format_timedelta(details[6], details[8])
                details_str += f"Resolution Time: {resolution_time}"

            Messagebox.show_info(details_str, f"Ticket #{ticket_id} Details")
            
    def assign_ticket_window(self):
        """Opens a window to assign a selected ticket to an agent."""
        selected_item = self.tickets_tree.focus()
        if not selected_item:
            Messagebox.show_warning("Please select a ticket to assign.", "No Selection")
            return
        ticket_id = int(self.tickets_tree.item(selected_item)['values'][0])

        assign_win = tb.Toplevel(self)
        assign_win.title(f"Assign Ticket #{ticket_id}")
        assign_win.geometry("300x150")

        tb.Label(assign_win, text="Select Agent:").pack(pady=10)
        
        agents = self.controller.db.get_users_by_role('agent')
        agent_names = [agent[1] for agent in agents]
        
        agent_combobox = tb.Combobox(assign_win, values=agent_names, state="readonly", bootstyle="info")
        agent_combobox.pack(pady=5)
        
        def do_assign():
            selected_agent_name = agent_combobox.get()
            if not selected_agent_name:
                Messagebox.show_error("Please select an agent.", "Error")
                return
            
            # Find agent ID from name
            agent_id = next((agent[0] for agent in agents if agent[1] == selected_agent_name), None)

            if agent_id:
                self.controller.db.assign_ticket(ticket_id, agent_id)
                Messagebox.show_info(f"Ticket #{ticket_id} assigned to {selected_agent_name}.", "Success")
                self.refresh_tickets_list()
                assign_win.destroy()
        
        tb.Button(assign_win, text="Assign", command=do_assign, bootstyle="success").pack(pady=10)

    def populate_users_tab(self):
        """Create and fill the 'Manage Users' tab."""
        # Form for adding new agents
        form_frame = tb.LabelFrame(self.users_tab, text="Add New Agent", padding="10", bootstyle="primary")
        form_frame.pack(fill="x", pady=10)

        tb.Label(form_frame, text="Username:").grid(row=0, column=0, padx=5, sticky="w")
        self.agent_username_entry = tb.Entry(form_frame)
        self.agent_username_entry.grid(row=0, column=1, padx=5, pady=5)
        
        tb.Label(form_frame, text="Password:").grid(row=1, column=0, padx=5, sticky="w")
        self.agent_password_entry = tb.Entry(form_frame, show="*")
        self.agent_password_entry.grid(row=1, column=1, padx=5, pady=5)
        
        tb.Button(form_frame, text="Create Agent", command=self.create_agent, bootstyle="success").grid(row=2, columnspan=2, pady=10)

        # User stats
        self.stats_frame = tb.LabelFrame(self.users_tab, text="User Statistics", padding="10", bootstyle="info")
        self.stats_frame.pack(fill="x", pady=(20, 5))
        self.agent_count_label = tb.Label(self.stats_frame, text="...")
        self.agent_count_label.pack(anchor="w")
        self.requester_count_label = tb.Label(self.stats_frame, text="...")
        self.requester_count_label.pack(anchor="w")

        # Treeview for displaying agents
        tb.Label(self.users_tab, text="Existing Agents", font=("Arial", 12)).pack(pady=(20, 5))
        self.agents_tree = tb.Treeview(self.users_tab, columns=("id", "username"), show="headings", bootstyle="primary")
        self.agents_tree.heading("id", text="ID")
        self.agents_tree.heading("username", text="Username")
        self.agents_tree.pack(expand=True, fill="both")
        self.refresh_agents_list()
        self.refresh_user_counts()

    def create_agent(self):
        """Handles the creation of a new agent user."""
        username = self.agent_username_entry.get()
        password = self.agent_password_entry.get()
        if not username or not password:
            Messagebox.show_error("Username and password are required.", "Error")
            return

        success, message = self.controller.db.register_user(username, password, role='agent')
        if success:
            Messagebox.show_info("Agent created successfully.", "Success")
            self.agent_username_entry.delete(0, 'end')
            self.agent_password_entry.delete(0, 'end')
            self.refresh_agents_list()
            self.refresh_user_counts()
        else:
            Messagebox.show_error(message, "Error")
            
    def refresh_agents_list(self):
        """Clears and re-populates the agents treeview."""
        for item in self.agents_tree.get_children():
            self.agents_tree.delete(item)
        for agent in self.controller.db.get_users_by_role('agent'):
            self.agents_tree.insert("", "end", values=agent)
            
    def refresh_user_counts(self):
        """Updates the labels displaying user counts."""
        counts = self.controller.db.count_users()
        self.agent_count_label.config(text=f"Total Agents: {counts.get('agent', 0)}")
        self.requester_count_label.config(text=f"Total Requesters: {counts.get('requester', 0)}")

    def populate_reports_tab(self):
        """Create and fill the 'Reports' tab."""
        button_frame = tb.Frame(self.reports_tab)
        button_frame.pack(pady=20, fill='x', anchor='center')

        tb.Button(button_frame, text="Generate 'Tickets Resolved This Week' Report", command=self.generate_weekly_report, bootstyle="primary").pack(side="left", padx=10)
        tb.Button(button_frame, text="Export to PDF", command=self.generate_pdf_report, bootstyle="success").pack(side="left", padx=10)
        
        columns = ("id", "title", "agent", "resolved_at")
        self.report_tree = tb.Treeview(self.reports_tab, columns=columns, show="headings", bootstyle="info")
        for col in columns:
            self.report_tree.heading(col, text=col.replace('_', ' ').title())
        self.report_tree.pack(expand=True, fill="both")

    def generate_weekly_report(self):
        """Fetches and displays the weekly report data."""
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        report_data = self.controller.db.get_weekly_report()
        for row in report_data:
            self.report_tree.insert("", "end", values=row)
        Messagebox.show_info(f"Found {len(report_data)} tickets resolved in the last 7 days.", "Report Generated")

    def generate_pdf_report(self):
        """Generates a PDF file from the current report data."""
        if not FPDF_AVAILABLE:
            Messagebox.show_error("FPDF library not found. Please install it using: pip install fpdf", "Error")
            return
            
        report_data = [self.report_tree.item(item)['values'] for item in self.report_tree.get_children()]
        
        if not report_data:
            Messagebox.show_warning("There is no report data to export. Please generate a report first.", "No Data")
            return

        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Weekly Resolved Tickets Report", 0, 1, 'C')
        pdf.ln(10)
        
        # Table Header
        pdf.set_font("Arial", 'B', 10)
        col_widths = [15, 80, 40, 50]
        headers = ["ID", "Title", "Agent", "Resolved At"]
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
        pdf.ln()
        
        # Table Rows
        pdf.set_font("Arial", '', 10)
        for row in report_data:
            for i, item in enumerate(row):
                pdf.cell(col_widths[i], 10, str(item), 1, 0)
            pdf.ln()
            
        filename = f"weekly_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        try:
            pdf.output(filename)
            Messagebox.show_info(f"Report successfully saved as {filename}", "Success")
        except Exception as e:
            Messagebox.show_error(f"Could not save PDF file: {e}", "Error")

    def populate_performance_tab(self):
        """Create and fill the 'Performance' tab."""
        tb.Button(self.performance_tab, text="Generate Agent Performance Report", command=self.generate_performance_report, bootstyle="primary").pack(pady=20)
        
        columns = ("agent", "assigned", "resolved", "avg_resolution_time")
        self.perf_tree = tb.Treeview(self.performance_tab, columns=columns, show="headings", bootstyle="success")
        self.perf_tree.heading("agent", text="Agent")
        self.perf_tree.heading("assigned", text="Assigned Tickets")
        self.perf_tree.heading("resolved", text="Resolved Tickets")
        self.perf_tree.heading("avg_resolution_time", text="Avg. Resolution Time")
        self.perf_tree.pack(expand=True, fill="both")

    def generate_performance_report(self):
        """Fetches and displays agent performance data."""
        for item in self.perf_tree.get_children():
            self.perf_tree.delete(item)
        
        report_data = self.controller.db.get_agent_performance_report()
        
        for row in report_data:
            agent, assigned, resolved, avg_days = row
            
            resolved = resolved or 0 # Handle None from SUM if no tickets are resolved
            
            if avg_days is not None:
                days = int(avg_days)
                hours = (avg_days - days) * 24
                time_str = f"{days}d {round(hours)}h"
            else:
                time_str = "N/A"
                
            self.perf_tree.insert("", "end", values=(agent, assigned, resolved, time_str))
            
        Messagebox.show_info(f"Performance report for {len(report_data)} agents has been generated.", "Report Generated")


class AgentDashboard(ttk.Frame):
    """Agent dashboard to view assigned tickets and update their status."""
    def __init__(self, parent, controller):
        super().__init__(parent, padding="10")
        self.controller = controller
        
        header_frame = tb.Frame(self)
        header_frame.pack(fill='x', pady=5)
        
        tb.Label(header_frame, text=f"Agent Dashboard - Welcome, {self.controller.current_user['username']}!", font=("Arial", 16), bootstyle="primary").pack(side="left")
        tb.Button(header_frame, text="Logout", command=controller.logout, bootstyle="danger").pack(side="right")
        
        tb.Label(self, text="My Assigned Tickets", font=("Arial", 12), bootstyle="info").pack(pady=10)

        columns = ("id", "title", "status", "requester", "created_at")
        self.tickets_tree = tb.Treeview(self, columns=columns, show="headings", bootstyle="primary")
        for col in columns:
            self.tickets_tree.heading(col, text=col.replace('_', ' ').title())
            self.tickets_tree.column(col, width=120)
        self.tickets_tree.pack(expand=True, fill="both")
        self.refresh_tickets_list()

        action_frame = tb.Frame(self, padding="10")
        action_frame.pack(fill="x")
        
        tb.Button(action_frame, text="View Details", command=self.view_ticket_details, bootstyle="info").pack(side="left", padx=5)
        tb.Button(action_frame, text="Update Status", command=self.update_status_window, bootstyle="success").pack(side="left", padx=5)
        tb.Button(action_frame, text="Refresh", command=self.refresh_tickets_list, bootstyle="secondary").pack(side="left", padx=5)

    def refresh_tickets_list(self):
        """Refreshes the list of assigned tickets."""
        agent_id = self.controller.current_user['id']
        for item in self.tickets_tree.get_children():
            self.tickets_tree.delete(item)
        for ticket in self.controller.db.get_agent_tickets(agent_id):
            self.tickets_tree.insert("", "end", values=ticket)
            
    def view_ticket_details(self):
        """Shows full details of a selected ticket."""
        selected_item = self.tickets_tree.focus()
        if not selected_item:
            Messagebox.show_warning("Please select a ticket to view.", "No Selection")
            return
        ticket_id = int(self.tickets_tree.item(selected_item)['values'][0])
        details = self.controller.db.get_ticket_details(ticket_id)
        if details:
            details_str = (
                f"ID: {details[0]}\n"
                f"Title: {details[1]}\n"
                f"Description: {details[2]}\n"
                f"Status: {details[3]}\n"
                f"Requester: {details[4]}\n"
                f"Created At: {details[6]}\n"
            )

            if details[8]: # resolved_at is not null
                resolution_time = format_timedelta(details[6], details[8])
                details_str += f"Resolution Time: {resolution_time}"

            Messagebox.show_info(details_str, f"Ticket #{ticket_id} Details")

    def update_status_window(self):
        """Opens a window to update the status of a selected ticket."""
        selected_item = self.tickets_tree.focus()
        if not selected_item:
            Messagebox.show_warning("Please select a ticket.", "No Selection")
            return
        # Ensure ticket_id is treated as an integer for reliability
        ticket_id = int(self.tickets_tree.item(selected_item)['values'][0])
        current_status = self.tickets_tree.item(selected_item)['values'][2]

        update_win = tb.Toplevel(self)
        update_win.title(f"Update Status for Ticket #{ticket_id}")
        update_win.geometry("300x150")

        tb.Label(update_win, text=f"Current Status: {current_status}").pack(pady=5)
        tb.Label(update_win, text="New Status:").pack(pady=5)

        statuses = ["Open", "In Progress", "Resolved"]
        status_combobox = tb.Combobox(update_win, values=statuses, state="readonly", bootstyle="info")
        status_combobox.pack(pady=5)
        
        def do_update():
            new_status = status_combobox.get()
            if not new_status:
                Messagebox.show_error("Please select a new status.", "Error")
                return
            
            self.controller.db.update_ticket_status(ticket_id, new_status)
            Messagebox.show_info(f"Ticket #{ticket_id} status updated to '{new_status}'.", "Success")
            self.refresh_tickets_list()
            update_win.destroy()

        tb.Button(update_win, text="Update", command=do_update, bootstyle="success").pack(pady=10)


class RequesterDashboard(ttk.Frame):
    """Requester dashboard to view their tickets and create new ones."""
    def __init__(self, parent, controller):
        super().__init__(parent, padding="10")
        self.controller = controller

        header_frame = tb.Frame(self)
        header_frame.pack(fill='x', pady=5)
        
        tb.Label(header_frame, text=f"Requester Dashboard - Welcome, {self.controller.current_user['username']}!", font=("Arial", 16), bootstyle="primary").pack(side="left")
        tb.Button(header_frame, text="Logout", command=controller.logout, bootstyle="danger").pack(side="right")
        
        # Split window into two parts
        main_pane = tb.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(expand=True, fill="both")
        
        # Left side: Create Ticket
        create_frame = tb.LabelFrame(main_pane, text="Create New Ticket", padding="10", bootstyle="primary")
        main_pane.add(create_frame, weight=1)
        
        tb.Label(create_frame, text="Title:").pack(anchor="w")
        self.title_entry = tb.Entry(create_frame)
        self.title_entry.pack(fill="x", pady=5)
        
        tb.Label(create_frame, text="Description:").pack(anchor="w")
        self.desc_text = tk.Text(create_frame, height=10)
        self.desc_text.pack(fill="both", expand=True, pady=5)
        
        tb.Button(create_frame, text="Submit Ticket", command=self.submit_ticket, bootstyle="success").pack(pady=10)

        # Right side: My Tickets
        list_frame = tb.LabelFrame(main_pane, text="My Submitted Tickets", padding="10", bootstyle="info")
        main_pane.add(list_frame, weight=2)
        
        columns = ("id", "title", "status", "agent", "created_at")
        self.tickets_tree = tb.Treeview(list_frame, columns=columns, show="headings", bootstyle="info")
        for col in columns:
            self.tickets_tree.heading(col, text=col.replace('_', ' ').title())
            self.tickets_tree.column(col, width=100)
        
        # Define tags for status colors
        self.tickets_tree.tag_configure('Open', background='red', foreground='white')
        self.tickets_tree.tag_configure('In Progress', background='orange', foreground='black')
        self.tickets_tree.tag_configure('Resolved', background='green', foreground='white')
        
        self.tickets_tree.pack(expand=True, fill="both")
        
        tb.Button(list_frame, text="Refresh", command=self.refresh_tickets_list, bootstyle="secondary").pack(pady=5, anchor="e")
        self.refresh_tickets_list()

    def submit_ticket(self):
        """Submits a new ticket to the database."""
        title = self.title_entry.get()
        description = self.desc_text.get("1.0", "end-1c")
        
        if not title or not description:
            Messagebox.show_error("Title and description cannot be empty.", "Error")
            return
            
        requester_id = self.controller.current_user['id']
        self.controller.db.create_ticket(title, description, requester_id)
        
        Messagebox.show_info("Ticket submitted successfully!", "Success")
        self.title_entry.delete(0, 'end')
        self.desc_text.delete("1.0", "end")
        self.refresh_tickets_list()
        
    def refresh_tickets_list(self):
        """Refreshes the list of submitted tickets with status colors."""
        requester_id = self.controller.current_user['id']
        for item in self.tickets_tree.get_children():
            self.tickets_tree.delete(item)
        for ticket in self.controller.db.get_requester_tickets(requester_id):
            # ticket values are (id, title, status, agent, created_at)
            status = ticket[2]
            self.tickets_tree.insert("", "end", values=ticket, tags=(status,))