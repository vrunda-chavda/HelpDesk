This is a desktop application for managing IT help desk tickets, built with Python's tkinter library for the GUI and sqlite3 for the database.

Features:
Three User Roles: Admin, Agent, and Requester with different levels of access and functionality.
Admin Dashboard: View all tickets, assign tickets to agents, create new agent accounts, view user counts, and generate reports.
Agent Dashboard: View and update the status of assigned tickets.
Requester Dashboard: Create new tickets and view the status of submitted tickets.
Secure Authentication: Passwords are hashed before being stored in the database.
Resolution Time Tracking: Automatically calculates and displays the time taken to resolve a ticket.
PDF Reporting: Admins can export the weekly report of resolved tickets to a PDF file.

Prerequisites
Before running the application, you need to install the fpdf library, which is used for generating PDF reports.
pip install fpdf

Passwords:
Admin:  Username-admin  password-admin

How to Run the Application
Install Prerequisites: Open your terminal and run the command in the "Prerequisites" section above.
Save the files: Make sure all three Python files (main.py, gui.py, database.py) are in the same directory.
Open your terminal: Navigate to the directory where you saved the files.
Run the main script: Execute the following command:
python main.py
The application window will appear. The ticketing_system.db file will be created automatically in the same directory if it doesn't exist.

The application window will appear. The ticketing_system.db file will be created automatically in the same directory if it doesn't exist.
