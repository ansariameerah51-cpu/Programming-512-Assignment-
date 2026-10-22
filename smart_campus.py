"""
Smart Campus Resource Booking System - Programming 512
Run with: python smart_campus.py
Uses only Python standard-library modules: tkinter, sqlite3, datetime, hashlib.
Demo administrator: admin / Admin123!
Demo system operator: operator / Operator123!
Change demo passwords before real use.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib
from datetime import datetime, timedelta

DB_NAME = "smart_campus.db"

# Campus policies are kept separate from the main booking logic so they can be changed easily.
CAMPUS_POLICIES = {
    "Centurion": {"max_hours": 4, "open": 8, "close": 18, "description": "Maximum 4 hours; bookings 08:00-18:00"},
    "Umhlanga": {"max_hours": 3, "open": 9, "close": 17, "description": "Maximum 3 hours; bookings 09:00-17:00"},
    "Cape Town": {"max_hours": 2, "open": 8, "close": 16, "description": "Maximum 2 hours; bookings 08:00-16:00"},
}


def password_hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class Database:
    def __init__(self, filename=DB_NAME):
        self.conn = sqlite3.connect(filename)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
        self.seed_data()

    def create_tables(self):
        self.conn.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Lecturer','Campus Administrator','System Operator')),
            campus TEXT
        );
        CREATE TABLE IF NOT EXISTS campuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            max_hours INTEGER NOT NULL,
            open_hour INTEGER NOT NULL,
            close_hour INTEGER NOT NULL,
            policy TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            campus TEXT NOT NULL,
            description TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            campus TEXT NOT NULL,
            booking_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            duration REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TEXT NOT NULL,
            FOREIGN KEY(resource_id) REFERENCES resources(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)
        self.conn.commit()

    def seed_data(self):
        for name, p in CAMPUS_POLICIES.items():
            self.conn.execute("INSERT OR IGNORE INTO campuses(name,max_hours,open_hour,close_hour,policy) VALUES(?,?,?,?,?)",
                              (name, p["max_hours"], p["open"], p["close"], p["description"]))
        # Demo staff accounts let the lecturer, administrator and operator workflows be tested.
        demos = [
            ("admin", "Admin123!", "Demo Campus Administrator", "Campus Administrator", "Centurion"),
            ("operator", "Operator123!", "Demo System Operator", "System Operator", None),
        ]
        for username, pw, full, role, campus in demos:
            self.conn.execute("INSERT OR IGNORE INTO users(username,password_hash,full_name,role,campus) VALUES(?,?,?,?,?)",
                              (username, password_hash(pw), full, role, campus))
        examples = [
            ("CEN-LAB-01", "Computer Lab 1", "Computer Laboratory", "Centurion", "Main computer laboratory"),
            ("CEN-PROJ-01", "Projector 1", "Projector", "Centurion", "Portable multimedia projector"),
            ("UMB-SEM-01", "Seminar Room 1", "Seminar Room", "Umhlanga", "Room for meetings and seminars"),
            ("UMB-LAB-01", "Computer Lab 1", "Computer Laboratory", "Umhlanga", "Computer laboratory"),
            ("CPT-PRES-01", "Presentation Kit 1", "Presentation Equipment", "Cape Town", "Screen and presentation kit"),
            ("CPT-SEM-01", "Seminar Room 1", "Seminar Room", "Cape Town", "Small seminar room"),
        ]
        for row in examples:
            self.conn.execute("INSERT OR IGNORE INTO resources(resource_code,name,resource_type,campus,description) VALUES(?,?,?,?,?)", row)
        self.conn.commit()

    def close(self):
        self.conn.close()


class User:
    def __init__(self, record):
        self.id = record["id"]
        self.username = record["username"]
        self.full_name = record["full_name"]
        self.role = record["role"]
        self.campus = record["campus"]

    def can_manage_resources(self):
        return self.role in ("Campus Administrator", "System Operator")

    def can_view_all_reports(self):
        return self.role == "System Operator"


class Lecturer(User):
    """Lecturer inherits shared account details from User."""
    pass


class CampusAdministrator(User):
    pass


class SystemOperator(User):
    pass


class SmartCampusApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Campus Resource Booking System")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)
        self.db = Database()
        self.user = None
        self.active_campus = None
        self.setup_style()
        self.show_login()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Arial", 18, "bold"))
        style.configure("Heading.TLabel", font=("Arial", 12, "bold"))
        style.configure("Treeview", rowheight=25)

    def clear(self):
        for child in self.root.winfo_children():
            child.destroy()

    def show_login(self):
        self.clear()
        outer = ttk.Frame(self.root, padding=35)
        outer.pack(expand=True)
        ttk.Label(outer, text="SMART CAMPUS", style="Title.TLabel").pack(pady=(0, 5))
        ttk.Label(outer, text="Resource Booking System").pack(pady=(0, 20))
        form = ttk.Frame(outer, padding=20)
        form.pack()
        ttk.Label(form, text="Username").grid(row=0, column=0, sticky="w", pady=7)
        self.login_username = ttk.Entry(form, width=32)
        self.login_username.grid(row=0, column=1, pady=7, padx=8)
        ttk.Label(form, text="Password").grid(row=1, column=0, sticky="w", pady=7)
        self.login_password = ttk.Entry(form, width=32, show="*")
        self.login_password.grid(row=1, column=1, pady=7, padx=8)
        ttk.Button(form, text="Log in", command=self.login).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 5))
        ttk.Button(form, text="Register as Lecturer", command=self.show_register).grid(row=3, column=0, columnspan=2, sticky="ew")
        ttk.Label(outer, text="Demo admin: admin / Admin123!     Demo operator: operator / Operator123!", foreground="#555").pack(pady=18)
        self.login_password.bind("<Return>", lambda _e: self.login())

    def login(self):
        username = self.login_username.get().strip()
        password = self.login_password.get()
        if not username or not password:
            messagebox.showwarning("Missing details", "Enter your username and password.")
            return
        row = self.db.conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?",
                                   (username, password_hash(password))).fetchone()
        if not row:
            messagebox.showerror("Login failed", "Incorrect username or password.")
            return
        role_classes = {"Lecturer": Lecturer, "Campus Administrator": CampusAdministrator, "System Operator": SystemOperator}
        self.user = role_classes[row["role"]](row)
        self.active_campus = self.user.campus or "Centurion"
        self.show_dashboard()

    def show_register(self):
        self.clear()
        frame = ttk.Frame(self.root, padding=30)
        frame.pack(expand=True)
        ttk.Label(frame, text="Lecturer Registration", style="Title.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 18))
        fields = {}
        for i, label in enumerate(("Full name", "Username", "Password"), start=1):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=7)
            entry = ttk.Entry(frame, width=32, show="*" if label == "Password" else "")
            entry.grid(row=i, column=1, pady=7, padx=10)
            fields[label] = entry
        ttk.Label(frame, text="Home campus").grid(row=4, column=0, sticky="w", pady=7)
        campus = ttk.Combobox(frame, values=list(CAMPUS_POLICIES), state="readonly", width=29)
        campus.set("Centurion")
        campus.grid(row=4, column=1, pady=7, padx=10)
        def register():
            full = fields["Full name"].get().strip()
            username = fields["Username"].get().strip()
            pw = fields["Password"].get()
            if not full or not username or not pw:
                messagebox.showwarning("Missing details", "Complete every field.")
                return
            if len(pw) < 6:
                messagebox.showwarning("Password too short", "Use at least 6 characters.")
                return
            try:
                self.db.conn.execute("INSERT INTO users(username,password_hash,full_name,role,campus) VALUES(?,?,?,?,?)",
                                     (username, password_hash(pw), full, "Lecturer", campus.get()))
                self.db.conn.commit()
                messagebox.showinfo("Registered", "Lecturer account created. You can now log in.")
                self.show_login()
            except sqlite3.IntegrityError:
                messagebox.showerror("Username unavailable", "That username already exists. Choose another.")
        ttk.Button(frame, text="Create account", command=register).grid(row=5, column=0, columnspan=2, sticky="ew", pady=12)
        ttk.Button(frame, text="Back to login", command=self.show_login).grid(row=6, column=0, columnspan=2, sticky="ew")

    def show_dashboard(self):
        self.clear()
        header = ttk.Frame(self.root, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text="Smart Campus Resource Booking System", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text=f"{self.user.full_name}  |  {self.user.role}").pack(side="right")
        bar = ttk.Frame(self.root, padding=(16, 4))
        bar.pack(fill="x")
        ttk.Label(bar, text="Active campus:", style="Heading.TLabel").pack(side="left")
        campus_values = list(CAMPUS_POLICIES)
        self.campus_combo = ttk.Combobox(bar, values=campus_values, state="readonly", width=18)
        self.campus_combo.set(self.active_campus)
        self.campus_combo.pack(side="left", padx=8)
        if self.user.role == "Campus Administrator":
            self.campus_combo.configure(state="disabled")
        else:
            self.campus_combo.bind("<<ComboboxSelected>>", self.change_campus)
        self.policy_label = ttk.Label(bar, text="")
        self.policy_label.pack(side="left", padx=12)
        ttk.Button(bar, text="Log out", command=self.logout).pack(side="right")
        self.update_policy_label()

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=16, pady=12)
        self.resources_tab = ttk.Frame(notebook, padding=12)
        self.bookings_tab = ttk.Frame(notebook, padding=12)
        self.reports_tab = ttk.Frame(notebook, padding=12)
        notebook.add(self.resources_tab, text="Resources")
        notebook.add(self.bookings_tab, text="Bookings")
        if self.user.role in ("Campus Administrator", "System Operator"):
            notebook.add(self.reports_tab, text="Reports")
        self.build_resources_tab()
        self.build_bookings_tab()
        if self.user.role in ("Campus Administrator", "System Operator"):
            self.build_reports_tab()

    def change_campus(self, _event=None):
        self.active_campus = self.campus_combo.get()
        self.update_policy_label()
        self.refresh_resources()
        self.refresh_bookings()
        if self.user.role in ("Campus Administrator", "System Operator"):
            self.refresh_reports()

    def update_policy_label(self):
        p = CAMPUS_POLICIES[self.active_campus]
        self.policy_label.configure(text=f"Policy: {p['description']}")

    def logout(self):
        self.user = None
        self.active_campus = None
        self.show_login()

    def build_resources_tab(self):
        top = ttk.Frame(self.resources_tab)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Campus resources", style="Heading.TLabel").pack(side="left")
        if self.user.can_manage_resources():
            ttk.Button(top, text="Add resource", command=self.add_resource).pack(side="right", padx=3)
            ttk.Button(top, text="Update selected", command=self.update_resource).pack(side="right", padx=3)
            ttk.Button(top, text="Remove selected", command=self.remove_resource).pack(side="right", padx=3)
        cols = ("id", "code", "name", "type", "campus", "description")
        self.resource_tree = ttk.Treeview(self.resources_tab, columns=cols, show="headings", height=15)
        headings = {"id":"ID", "code":"Resource Code", "name":"Name", "type":"Type", "campus":"Campus", "description":"Description"}
        widths = {"id":45, "code":130, "name":180, "type":170, "campus":110, "description":250}
        for col in cols:
            self.resource_tree.heading(col, text=headings[col])
            self.resource_tree.column(col, width=widths[col], anchor="w")
        self.resource_tree.pack(fill="both", expand=True)
        ttk.Label(self.resources_tab, text="Lecturers can select a resource and create a booking from the Bookings tab.").pack(anchor="w", pady=(8, 0))
        self.refresh_resources()

    def refresh_resources(self):
        if not hasattr(self, "resource_tree") or not self.resource_tree.winfo_exists():
            return
        for item in self.resource_tree.get_children(): self.resource_tree.delete(item)
        if self.user.role == "System Operator":
            rows = self.db.conn.execute("SELECT * FROM resources ORDER BY campus,name").fetchall()
        else:
            rows = self.db.conn.execute("SELECT * FROM resources WHERE campus=? ORDER BY name", (self.active_campus,)).fetchall()
        for r in rows:
            self.resource_tree.insert("", "end", values=(r["id"],r["resource_code"],r["name"],r["resource_type"],r["campus"],r["description"]))

    def selected_resource(self):
        selection = self.resource_tree.selection()
        if not selection:
            messagebox.showwarning("Select resource", "Select a resource first.")
            return None
        return self.resource_tree.item(selection[0], "values")

    def resource_dialog(self, existing=None):
        win = tk.Toplevel(self.root)
        win.title("Resource details")
        win.transient(self.root); win.grab_set()
        frame = ttk.Frame(win, padding=18); frame.pack(fill="both", expand=True)
        labels = ["Resource code", "Name", "Type", "Campus", "Description"]
        entries = {}
        initial = list(existing[1:]) if existing else ["", "", "Computer Laboratory", self.active_campus, ""]
        for i, label in enumerate(labels):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=6)
            if label == "Campus":
                widget = ttk.Combobox(frame, values=list(CAMPUS_POLICIES), state="readonly", width=28)
                widget.set(initial[3] or self.active_campus)
            elif label == "Type":
                widget = ttk.Combobox(frame, values=["Computer Laboratory", "Projector", "Seminar Room", "Presentation Equipment", "Other"], width=28)
                widget.set(initial[2] or "Other")
            else:
                widget = ttk.Entry(frame, width=31)
                widget.insert(0, initial[i] or "")
            widget.grid(row=i, column=1, pady=6, padx=8)
            entries[label] = widget
        def save():
            vals = [entries[x].get().strip() for x in labels]
            if not vals[0] or not vals[1] or not vals[2] or not vals[3]:
                messagebox.showwarning("Missing details", "Code, name, type and campus are required.", parent=win); return
            try:
                if existing:
                    self.db.conn.execute("UPDATE resources SET resource_code=?,name=?,resource_type=?,campus=?,description=? WHERE id=?", (*vals, existing[0]))
                else:
                    self.db.conn.execute("INSERT INTO resources(resource_code,name,resource_type,campus,description) VALUES(?,?,?,?,?)", vals)
                self.db.conn.commit(); win.destroy(); self.refresh_resources()
                messagebox.showinfo("Saved", "Resource details saved.")
            except sqlite3.IntegrityError:
                messagebox.showerror("Duplicate code", "Resource code must be unique.", parent=win)
        ttk.Button(frame, text="Save", command=save).grid(row=len(labels), column=0, columnspan=2, sticky="ew", pady=12)

    def add_resource(self):
        self.resource_dialog()

    def update_resource(self):
        selected = self.selected_resource()
        if selected: self.resource_dialog(selected)

    def remove_resource(self):
        selected = self.selected_resource()
        if not selected: return
        used = self.db.conn.execute("SELECT COUNT(*) FROM bookings WHERE resource_id=?", (selected[0],)).fetchone()[0]
        if used:
            messagebox.showerror("Cannot remove", "This resource has booking records. Keep it to preserve history.")
            return
        if messagebox.askyesno("Confirm removal", f"Remove {selected[2]} ({selected[1]})?"):
            self.db.conn.execute("DELETE FROM resources WHERE id=?", (selected[0],)); self.db.conn.commit(); self.refresh_resources()

    def build_bookings_tab(self):
        top = ttk.Frame(self.bookings_tab); top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Booking management", style="Heading.TLabel").pack(side="left")
        if self.user.role == "Lecturer":
            ttk.Button(top, text="Create booking", command=self.create_booking).pack(side="right", padx=3)
            ttk.Button(top, text="Cancel selected future booking", command=self.cancel_booking).pack(side="right", padx=3)
        ttk.Button(top, text="Refresh", command=self.refresh_bookings).pack(side="right", padx=3)
        cols = ("id", "resource", "lecturer", "campus", "date", "start", "duration", "status")
        self.booking_tree = ttk.Treeview(self.bookings_tab, columns=cols, show="headings", height=15)
        heads = {"id":"ID", "resource":"Resource", "lecturer":"Booked by", "campus":"Campus", "date":"Date", "start":"Start", "duration":"Hours", "status":"Status"}
        widths = {"id":45,"resource":180,"lecturer":150,"campus":100,"date":100,"start":80,"duration":70,"status":85}
        for c in cols:
            self.booking_tree.heading(c, text=heads[c]); self.booking_tree.column(c, width=widths[c], anchor="w")
        self.booking_tree.pack(fill="both", expand=True)
        self.refresh_bookings()

    def refresh_bookings(self):
        if not hasattr(self, "booking_tree") or not self.booking_tree.winfo_exists(): return
        for item in self.booking_tree.get_children(): self.booking_tree.delete(item)
        sql = """SELECT b.id,r.name AS resource,u.full_name AS lecturer,b.campus,b.booking_date,b.start_time,b.duration,b.status
                 FROM bookings b JOIN resources r ON r.id=b.resource_id JOIN users u ON u.id=b.user_id"""
        params = []
        if self.user.role == "Lecturer":
            sql += " WHERE b.user_id=?"; params.append(self.user.id)
        elif self.user.role == "Campus Administrator":
            sql += " WHERE b.campus=?"; params.append(self.user.campus)
        else:
            sql += " WHERE b.campus=?"; params.append(self.active_campus)
        sql += " ORDER BY b.booking_date DESC,b.start_time"
        for r in self.db.conn.execute(sql, params).fetchall():
            self.booking_tree.insert("", "end", values=(r["id"],r["resource"],r["lecturer"],r["campus"],r["booking_date"],r["start_time"],r["duration"],r["status"]))

    def create_booking(self):
        resources = self.db.conn.execute("SELECT * FROM resources WHERE campus=? ORDER BY name", (self.active_campus,)).fetchall()
        if not resources:
            messagebox.showinfo("No resources", "There are no resources registered at this campus."); return
        win = tk.Toplevel(self.root); win.title("Create booking"); win.transient(self.root); win.grab_set()
        frame = ttk.Frame(win, padding=20); frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"Booking policy: {CAMPUS_POLICIES[self.active_campus]['description']}", wraplength=380).grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,12))
        ttk.Label(frame, text="Resource").grid(row=1,column=0,sticky="w",pady=6)
        resource_combo = ttk.Combobox(frame, state="readonly", width=32, values=[f"{r['id']} - {r['resource_code']} - {r['name']}" for r in resources])
        resource_combo.current(0); resource_combo.grid(row=1,column=1,padx=8,pady=6)
        ttk.Label(frame, text="Date (YYYY-MM-DD)").grid(row=2,column=0,sticky="w",pady=6)
        date_entry = ttk.Entry(frame,width=35); date_entry.insert(0,datetime.now().strftime("%Y-%m-%d")); date_entry.grid(row=2,column=1,padx=8,pady=6)
        ttk.Label(frame, text="Start time (HH:MM)").grid(row=3,column=0,sticky="w",pady=6)
        time_entry = ttk.Entry(frame,width=35); time_entry.insert(0,"10:00"); time_entry.grid(row=3,column=1,padx=8,pady=6)
        ttk.Label(frame, text="Duration (hours)").grid(row=4,column=0,sticky="w",pady=6)
        duration_entry = ttk.Entry(frame,width=35); duration_entry.insert(0,"1"); duration_entry.grid(row=4,column=1,padx=8,pady=6)
        def save_booking():
            try:
                resource_id = int(resource_combo.get().split(" - ",1)[0])
                day = datetime.strptime(date_entry.get().strip(), "%Y-%m-%d").date()
                start = datetime.strptime(time_entry.get().strip(), "%H:%M")
                duration = float(duration_entry.get().strip())
                if duration <= 0: raise ValueError("Duration must be positive.")
            except (ValueError, IndexError):
                messagebox.showerror("Invalid input", "Enter a valid date, time and positive duration.", parent=win); return
            now = datetime.now()
            start_dt = datetime.combine(day, start.time())
            end_dt = start_dt + timedelta(hours=duration)
            policy = CAMPUS_POLICIES[self.active_campus]
            if start_dt <= now:
                messagebox.showerror("Invalid date/time", "Bookings must start in the future.", parent=win); return
            if duration > policy["max_hours"]:
                messagebox.showerror("Policy limit", f"Maximum duration at {self.active_campus} is {policy['max_hours']} hours.", parent=win); return
            if start.hour < policy["open"] or end_dt.hour + (1 if end_dt.minute else 0) > policy["close"] or end_dt.date() != day:
                messagebox.showerror("Outside booking hours", f"Bookings must fit within {policy['open']:02d}:00-{policy['close']:02d}:00 and end on the same day.", parent=win); return
            overlap = self.db.conn.execute("""SELECT COUNT(*) FROM bookings WHERE resource_id=? AND booking_date=? AND status='Active'
                AND time(start_time) < time(?) AND time(start_time, '+' || (duration*60) || ' minutes') > time(?)""",
                (resource_id, day.isoformat(), end_dt.strftime("%H:%M"), start.strftime("%H:%M"))).fetchone()[0]
            if overlap:
                messagebox.showerror("Resource unavailable", "This resource already has an overlapping booking.", parent=win); return
            self.db.conn.execute("INSERT INTO bookings(resource_id,user_id,campus,booking_date,start_time,duration,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                 (resource_id,self.user.id,self.active_campus,day.isoformat(),start.strftime("%H:%M"),duration,"Active",datetime.now().isoformat(timespec="seconds")))
            self.db.conn.commit(); win.destroy(); self.refresh_bookings()
            messagebox.showinfo("Booking created", "Your booking has been saved.")
        ttk.Button(frame,text="Confirm booking",command=save_booking).grid(row=5,column=0,columnspan=2,sticky="ew",pady=12)

    def cancel_booking(self):
        selection = self.booking_tree.selection()
        if not selection:
            messagebox.showwarning("Select booking", "Select a booking to cancel."); return
        values = self.booking_tree.item(selection[0], "values")
        booking_id = values[0]
        row = self.db.conn.execute("SELECT booking_date,start_time,status FROM bookings WHERE id=? AND user_id=?", (booking_id,self.user.id)).fetchone()
        if not row:
            messagebox.showerror("Not permitted", "You can only cancel your own bookings."); return
        start_dt = datetime.strptime(row["booking_date"]+" "+row["start_time"], "%Y-%m-%d %H:%M")
        if row["status"] != "Active" or start_dt <= datetime.now():
            messagebox.showerror("Cannot cancel", "Only active future bookings can be cancelled."); return
        if messagebox.askyesno("Cancel booking", "Cancel this future booking?"):
            self.db.conn.execute("UPDATE bookings SET status='Cancelled' WHERE id=?", (booking_id,)); self.db.conn.commit(); self.refresh_bookings()
            messagebox.showinfo("Cancelled", "Booking cancelled.")

    def build_reports_tab(self):
        ttk.Label(self.reports_tab, text="Campus usage reports", style="Heading.TLabel").pack(anchor="w",pady=(0,10))
        ttk.Button(self.reports_tab, text="Refresh reports", command=self.refresh_reports).pack(anchor="e",pady=(0,8))
        self.report_text = tk.Text(self.reports_tab, wrap="word", height=20, font=("Consolas", 10))
        self.report_text.pack(fill="both",expand=True)
        self.refresh_reports()

    def refresh_reports(self):
        if not hasattr(self,"report_text") or not self.report_text.winfo_exists(): return
        self.report_text.delete("1.0","end")
        campuses = list(CAMPUS_POLICIES) if self.user.role == "System Operator" else [self.user.campus]
        lines = []
        for campus in campuses:
            total = self.db.conn.execute("SELECT COUNT(*) FROM bookings WHERE campus=?",(campus,)).fetchone()[0]
            active = self.db.conn.execute("SELECT COUNT(*) FROM bookings WHERE campus=? AND status='Active'",(campus,)).fetchone()[0]
            avg = self.db.conn.execute("SELECT AVG(duration) FROM bookings WHERE campus=? AND status='Active'",(campus,)).fetchone()[0]
            most = self.db.conn.execute("""SELECT r.name,COUNT(*) AS uses FROM bookings b JOIN resources r ON r.id=b.resource_id
                       WHERE b.campus=? AND b.status='Active' GROUP BY r.id ORDER BY uses DESC LIMIT 1""",(campus,)).fetchone()
            lines.append(f"CAMPUS: {campus}\n{'-'*48}\nTotal bookings (including cancelled): {total}\nActive bookings: {active}\nAverage active booking duration: {avg:.2f} hours\nMost frequently used resource: {most['name']+' ('+str(most['uses'])+' bookings)' if most else 'No active bookings'}\nPolicy: {CAMPUS_POLICIES[campus]['description']}\n")
        if self.user.role == "System Operator":
            lines.append("CROSS-CAMPUS COMPARISON\n"+"-"*48)
            for campus in CAMPUS_POLICIES:
                count = self.db.conn.execute("SELECT COUNT(*) FROM bookings WHERE campus=? AND status='Active'",(campus,)).fetchone()[0]
                lines.append(f"{campus:<15} {count} active booking(s)")
            lines.append("\nCompare these totals with each campus's maximum duration and permitted booking hours.")
        self.report_text.insert("1.0","\n".join(lines))

    def on_close(self):
        self.db.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SmartCampusApp(root)
    root.mainloop()
