
import database as db
import auth
from config import DATABASE_PATH

# Ensure the database tables exist
db.init_db()

print("Database file:", DATABASE_PATH)

if auth.admin_exists("admin"):
    # Reset only the admin password; preserve all other records
    auth.change_password("admin", "admin123")
    print("Admin password has been reset.")
else:
    auth.create_admin("admin", "admin123", "Default Administrator")
    print("Default admin account created.")

print("Username: admin")
print("Password: admin123")
print("Login test:", auth.verify_admin("admin", "admin123"))
