import streamlit as st
import sqlite3
from datetime import datetime

# ---------------------------
# DATABASE SETUP
# ---------------------------
conn = sqlite3.connect('group_tracker.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    amount REAL,
    status TEXT,
    last_updated TEXT
)
''')
conn.commit()


# ---------------------------
# DATABASE FUNCTIONS
# ---------------------------
def format_datetime(timestamp):
    """Convert timestamp to dd/mm/yyyy, hh:mm AM/PM"""
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y, %I:%M %p")
    except Exception:
        return timestamp


def add_member(name, phone, amount=250):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO members (name, phone, amount, status, last_updated) VALUES (?, ?, ?, ?, ?)",
              (name, phone, amount, "Unpaid", now))
    conn.commit()


def update_member(member_id, name, phone, status, amount=250):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE members SET name=?, phone=?, amount=?, status=?, last_updated=? WHERE id=?",
              (name, phone, amount, status, now, member_id))
    conn.commit()


def delete_member(member_id):
    c.execute("DELETE FROM members WHERE id=?", (member_id,))
    conn.commit()


def get_all_members():
    c.execute("SELECT * FROM members")
    return c.fetchall()


def get_member_names():
    c.execute("SELECT id, name FROM members")
    return c.fetchall()


def get_stats():
    c.execute("SELECT COUNT(*), SUM(amount), SUM(CASE WHEN status='Paid' THEN amount ELSE 0 END) FROM members")
    total_members, total_amount, total_paid = c.fetchone()
    total_members = total_members or 0
    total_amount = total_amount or 0
    total_paid = total_paid or 0
    total_unpaid = total_amount - total_paid
    return total_members, total_amount, total_paid, total_unpaid


# ---------------------------
# STREAMLIT APP
# ---------------------------
st.set_page_config(page_title="Group Payment Tracker", page_icon="💰", layout="centered")

st.title("💰 Group Payment Tracker")

menu = st.sidebar.radio("Select Console", ["Admin Console", "Member Console"])

# ---------------------------
# ADMIN CONSOLE (with password)
# ---------------------------
if menu == "Admin Console":
    st.header("🧑‍💼 Admin Console")

    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        password = st.text_input("Enter Admin Password", type="password")
        if st.button("Login"):
            if password == "1234":
                st.session_state["admin_logged_in"] = True
                st.success("✅ Login successful! Welcome Admin.")
            else:
                st.error("❌ Incorrect password.")
    else:
        st.sidebar.success("Logged in as Admin ✅")

        option = st.radio("Choose Action", [
            "Add Member",
            "Edit / Delete Member",
            "View Logs / Reports",
            "Logout"
        ])

        # ----------------- ADD MEMBER -----------------
        if option == "Add Member":
            st.subheader("➕ Add New Member")
            name = st.text_input("Name")
            phone = st.text_input("Phone Number")

            if st.button("Add Member"):
                if name and phone:
                    add_member(name, phone)
                    st.success(f"✅ Member '{name}' added successfully with default amount 250!")
                else:
                    st.warning("Please fill all fields.")

        # ----------------- EDIT / DELETE MEMBER -----------------
        elif option == "Edit / Delete Member":
            st.subheader("✏️ Edit or ❌ Delete Member")

            members = get_member_names()
            if members:
                member_dict = {m[1]: m[0] for m in members}
                selected_name = st.selectbox("Select Member", list(member_dict.keys()))
                member_id = member_dict[selected_name]

                c.execute("SELECT * FROM members WHERE id=?", (member_id,))
                member_data = c.fetchone()

                name = st.text_input("Name", value=member_data[1])
                phone = st.text_input("Phone Number", value=member_data[2])
                status = st.selectbox("Status", ["Paid", "Unpaid"], index=0 if member_data[4] == "Paid" else 1)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Update Member"):
                        update_member(member_id, name, phone, status)
                        st.success(f"✅ Member '{name}' updated successfully!")

                with col2:
                    if st.button("🗑️ Delete Member"):
                        delete_member(member_id)
                        st.warning(f"❌ Member '{selected_name}' has been deleted.")
            else:
                st.info("No members available to edit or delete.")

        # ----------------- VIEW LOGS -----------------
        elif option == "View Logs / Reports":
            st.subheader("📊 Monthly and Overall Report")

            total_members, total_amount, total_paid, total_unpaid = get_stats()
            st.write(f"🧍 Total Members: **{total_members}**")
            st.write(f"💵 Total Expected Amount: **{total_amount} PKR**")
            st.write(f"✅ Total Paid Amount: **{total_paid} PKR**")
            st.write(f"❌ Remaining (Unpaid): **{total_unpaid} PKR**")

            st.divider()
            st.subheader("📅 Member Log Details")
            data = get_all_members()
            if data:
                formatted = []
                for d in data:
                    status_colored = f"<span style='color: green; font-weight: bold;'>Paid</span>" if d[4] == "Paid" else f"<span style='color: red; font-weight: bold;'>Unpaid</span>"
                    formatted.append([d[1], d[2], d[3], status_colored, format_datetime(d[5])])

                st.markdown(
                    "<table border='1' style='width:100%; text-align:center;'>"
                    "<tr><th>Name</th><th>Phone</th><th>Amount</th><th>Status</th><th>Last Updated</th></tr>" +
                    "".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>" for r in formatted]) +
                    "</table>",
                    unsafe_allow_html=True
                )
            else:
                st.info("No data available.")

        # ----------------- LOGOUT -----------------
        elif option == "Logout":
            st.session_state["admin_logged_in"] = False
            st.info("You have been logged out.")


# ---------------------------
# MEMBER CONSOLE
# ---------------------------
elif menu == "Member Console":
    st.header("👥 Member Console")
    st.subheader("📋 Payment Status of All Members")

    data = get_all_members()
    if data:
        formatted = []
        for d in data:
            status_colored = f"<span style='color: green; font-weight: bold;'>Paid</span>" if d[4] == "Paid" else f"<span style='color: red; font-weight: bold;'>Unpaid</span>"
            formatted.append([d[1], d[2], d[3], status_colored, format_datetime(d[5])])

        st.markdown(
            "<table border='1' style='width:100%; text-align:center;'>"
            "<tr><th>Name</th><th>Phone</th><th>Amount</th><th>Status</th><th>Last Updated</th></tr>" +
            "".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>" for r in formatted]) +
            "</table>",
            unsafe_allow_html=True
        )
    else:
        st.info("No members added yet.")
