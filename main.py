from database import Database
from gui import TicketingApp

if __name__ == "__main__":
    """
    Main entry point for the application.
    Initializes the database connection and starts the Tkinter main loop.
    """
    db_instance = Database()
    app = TicketingApp(db_instance)
    app.mainloop()
