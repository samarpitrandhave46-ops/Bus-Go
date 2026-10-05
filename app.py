"""BusGo – Bus Reservation System (Streamlit).  Run: streamlit run app.py"""
import json, re, time
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
import service

service.init()
st.set_page_config(page_title="BusGo", page_icon="🚌", layout="wide")

CSS = """
<style>
:root{--brand:#4F46E5;--soft:#EEF2FF}
.block-container{padding-top:1.5rem;max-width:1100px}
.card{background:var(--secondary-background-color);border-radius:16px;padding:16px 18px;margin-bottom:12px;
      border:1px solid rgba(128,128,128,.2)}
.hero{background:linear-gradient(135deg,#4F46E5,#7C3AED);color:#fff;border-radius:20px;padding:22px;margin-bottom:16px}
.hero h2,.hero p{color:#fff;margin:0}
.offer{background:linear-gradient(135deg,#F59E0B,#EF4444);color:#fff;border-radius:16px;padding:14px}
.chip{display:inline-block;padding:2px 10px;border-radius:99px;background:var(--brand);color:#fff;font-size:12px;margin-right:6px}
.price{font-size:22px;font-weight:700;color:var(--brand)}
.seat{display:inline-block;width:46px;height:40px;line-height:40px;text-align:center;border-radius:8px;margin:3px;
      font-size:12px;font-weight:600;border:1px solid #9994}
.s-av{background:#DCFCE7;color:#166534}.s-sel{background:#4F46E5;color:#fff}.s-bk{background:#9CA3AF;color:#fff}
.s-f{background:#FBCFE8;color:#9D174D}.s-m{background:#BFDBFE;color:#1E40AF}.gap{display:inline-block;width:30px}
.ok{text-align:center;font-size:64px}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)

S = st.session_state
for k, v in dict(user=None, page="home", search=None, bus=None, seats=[], pax=[], fare=None,
                 booking=None, recent=[], promo="").items():
    S.setdefault(k, v)


def go(p):
    S.page = p
    st.rerun()


def money(x):
    return f"₹{x:,.0f}"


# ================= AUTH =================
def auth_page():
    st.markdown('<div class="hero"><h2>🚌 BusGo</h2><p>Book bus tickets in seconds.</p></div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["Login", "Create account", "Forgot password"])
    with t1:
        with st.form("login"):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Login", type="primary", use_container_width=True):
                u = service.login(email, pw)
                if u:
                    S.user = u; S.page = "admin" if u["role"] == "admin" else "home"; st.rerun()
                st.error("Invalid email or password.")
        st.caption("Demo → user@busgo.com / user123 · admin@busgo.com / admin123")
        st.button("Continue with Google", disabled=True, help="Needs OAuth setup (st.login) – see notes.")
    with t2:
        with st.form("reg"):
            name = st.text_input("Full name")
            email = st.text_input("Email ", key="re")
            phone = st.text_input("Mobile number")
            p1 = st.text_input("Password ", type="password", key="p1")
            p2 = st.text_input("Confirm password", type="password")
            if st.form_submit_button("Create account", type="primary", use_container_width=True):
                if len(name.strip()) < 2: st.error("Enter your full name.")
                elif not re.match(r"[^@]+@[^@]+\.\w+", email): st.error("Invalid email.")
                elif not re.fullmatch(r"\d{10}", phone): st.error("Mobile must be 10 digits.")
                elif len(p1) < 6: st.error("Password needs 6+ characters.")
                elif p1 != p2: st.error("Passwords do not match.")
                else:
                    ok, msg = service.register(
    name.strip(),
    email,
    phone,
    p1
)
                    (st.success if ok else st.error)(msg)
    with t3:
        with st.form("fp"):
            e = st.text_input("Registered email", key="fe")
            ph = st.text_input("Registered mobile", key="fph")
            npw = st.text_input("New password", type="password", key="fnp")
            if st.form_submit_button("Reset password"):
                if len(npw) >= 6 and service.reset_password(e, ph, npw): st.success("Password updated.")
                else: st.error("Details don't match or password too short.")


# ================= USER PAGES =================
def home():
    cities = service.cities()
    st.markdown(f'<div class="hero"><h2>Hello, {S.user["name"].split()[0]} 👋</h2><p>Where are you going today?</p></div>',
                unsafe_allow_html=True)
    S.setdefault("f_from", "Mumbai"); S.setdefault("f_to", "Pune")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        src = c1.selectbox("From", cities, key="f_from")
        dst = c2.selectbox("To", cities, key="f_to")
        c3, c4 = st.columns(2)
        jd = c3.date_input("Journey date", date.today() + timedelta(days=1), min_value=date.today())
        n = c4.number_input("Passengers", 1, 6, 1)
        if st.button("🔍 Search Bus", type="primary", use_container_width=True):
            if src == dst: st.error("Origin and destination must differ.")
            else:
                S.search = dict(src=src, dst=dst, date=jd, n=int(n))
                r = f"{src} → {dst}"
                S.recent = ([r] + [x for x in S.recent if x != r])[:4]
                go("results")

    def setroute(a, b): S.f_from, S.f_to = a, b
    st.subheader("Popular routes")
    cols = st.columns(3)
    for i, (a, b) in enumerate([("Mumbai", "Pune"), ("Pune", "Mumbai"), ("Mumbai", "Nashik")]):
        cols[i].button(f"{a} → {b}", key=f"pop{i}", on_click=setroute, args=(a, b), use_container_width=True)
    if S.recent:
        st.subheader("Recent searches")
        st.write(" ".join(f'<span class="chip">{r}</span>' for r in S.recent), unsafe_allow_html=True)

    st.subheader("Offers")
    o1, o2 = st.columns(2)
    o1.markdown('<div class="offer"><b>BUSGO10</b><br>10% off on your booking</div>', unsafe_allow_html=True)
    o2.markdown('<div class="offer" style="background:linear-gradient(135deg,#059669,#0EA5E9)"><b>WELCOME50</b><br>5% off for new users</div>', unsafe_allow_html=True)

    up = [b for b in service.bookings_of(S.user["id"]) if service.group(b) == "Upcoming"]
    if up:
        b = sorted(up, key=lambda x: x["journey_date"])[0]
        st.subheader("Upcoming booking")
        st.markdown(f'<div class="card"><b>{b["src"]} → {b["dst"]}</b> · {b["journey_date"]} · {b["dep"]}<br>'
                    f'{b["operator"]} · Seats {", ".join(json.loads(b["seats"]))} · <span class="chip">{b["id"]}</span></div>',
                    unsafe_allow_html=True)
    q1, q2 = st.columns(2)
    if q1.button("🎫 My Bookings", use_container_width=True): go("bookings")
    if q2.button("👤 Profile", use_container_width=True): go("profile")


def results():
    s = S.search
    if not s: return go("home")
    if st.button("← Back"): go("home")
    st.subheader(f"{s['src']} → {s['dst']} · {s['date']:%d %b %Y}")
    d = service.search_buses(s["src"], s["dst"], s["date"])
    if d.empty:
        st.info("🚫 No buses on this route. Try another one."); return
    with st.expander("Filters & sorting", expanded=False):
        pr = st.slider("Max price (₹)", 100, int(d.price.max()) + 100, int(d.price.max()) + 100)
        types = st.multiselect("Bus type", sorted(d.bus_type.unique()))
        f1, f2 = st.columns(2)
        ac = f1.selectbox("AC", ["Any", "AC", "Non-AC"])
        kind = f2.selectbox("Seat kind", ["Any", "Seater", "Sleeper"])
        win = st.selectbox("Departure time", ["Any", "Morning (5–12)", "Afternoon (12–17)", "Evening (17–21)", "Night (21–5)"])
        awin = st.selectbox("Arrival time", ["Any", "Morning (5–12)", "Afternoon (12–17)", "Evening (17–21)", "Night (21–5)"])
        sort = st.radio("Sort by", ["Cheapest", "Earliest departure", "Shortest journey"], horizontal=True)

    def in_win(t, w):
        h = int(t[:2])
        return w == "Any" or {"M": 5 <= h < 12, "A": 12 <= h < 17, "E": 17 <= h < 21, "N": h >= 21 or h < 5}[w[0]]
    d = d[d.price <= pr]
    if types: d = d[d.bus_type.isin(types)]
    if ac != "Any": d = d[d.ac == (1 if ac == "AC" else 0)]
    if kind != "Any": d = d[d.seat_kind == kind]
    d = d[d.dep.apply(lambda t: in_win(t, win)) & d.arr.apply(lambda t: in_win(t, awin))]
    d = d.sort_values({"Cheapest": "price", "Earliest departure": "dep", "Shortest journey": "duration"}[sort])
    if d.empty:
        st.info("No buses match your filters."); return
    for _, b in d.iterrows():
        with st.container(border=True):
            a, c = st.columns([3, 1])
            a.markdown(f"**{b.operator}**  ⭐ {b.rating}  \n{b.bus_type}")
            a.markdown(f'<span class="chip">{"AC" if b.ac else "Non-AC"}</span><span class="chip">{b.seat_kind}</span>',
                       unsafe_allow_html=True)
            a.write(f"🕒 **{b.dep}** → **{b.arr}** ({service.fmt_dur(b.duration)})  ·  💺 {b.available} seats left")
            c.markdown(f'<div class="price">{money(b.price)}</div><small>onwards</small>', unsafe_allow_html=True)
            if c.button("View Seats", key=f"v{b.id}", type="primary", disabled=b.available < s["n"]):
                S.bus = b.to_dict(); S.seats = []; go("seats")


def seat_map(bus, jd, selected):
    taken = service.taken_seats(bus["id"], jd); res = service.reserved(bus["rows"]); html = ""
    for r in range(1, bus["rows"] + 1):
        for c in "ABCD":
            sid = f"{r}{c}"
            cls = "s-bk" if sid in taken else "s-sel" if sid in selected else "s-f" if res.get(sid) == "F" else \
                  "s-m" if res.get(sid) == "M" else "s-av"
            html += f'<span class="seat {cls}">{sid}</span>'
            if c == "B": html += '<span class="gap"></span>'
        html += "<br>"
    return html, taken, res


def seats():
    s, bus = S.search, S.bus
    if not bus: return go("home")
    if st.button("← Back to results"): go("results")
    st.subheader(f"{bus['operator']} · {s['src']} → {s['dst']}")
    st.caption(f"{s['date']:%d %b %Y} · Departs {bus['dep']} · Arrives {bus['arr']} · {bus['bus_type']}")
    html, taken, res = seat_map(bus, s["date"], S.seats)
    st.markdown('<span class="seat s-av">Free</span><span class="seat s-sel">Yours</span><span class="seat s-bk">Booked</span>'
                '<span class="seat s-f">Ladies</span><span class="seat s-m">Gents</span>', unsafe_allow_html=True)
    st.markdown(f'<div class="card" style="overflow-x:auto">{html}</div>', unsafe_allow_html=True)
    opts = [x for x in service.seat_labels(bus["rows"]) if x not in taken]
    S.seats = st.multiselect(f"Choose up to {s['n']} seat(s)", opts, default=[x for x in S.seats if x in opts],
                             max_selections=s["n"],
                             format_func=lambda x: x + (" (Ladies)" if res.get(x) == "F" else " (Gents)" if res.get(x) == "M" else ""))
    f = service.fare(bus["price"], len(S.seats))
    st.markdown(f'<div class="card"><b>Seats:</b> {", ".join(S.seats) or "—"} · <b>Count:</b> {len(S.seats)} · '
                f'<b>Total:</b> <span class="price">{money(f["base"])}</span></div>', unsafe_allow_html=True)
    if st.button("Continue", type="primary", use_container_width=True):
        if len(S.seats) != s["n"]: st.warning(f"Please select exactly {s['n']} seat(s).")
        else: S.pax = []; go("passengers")


def passengers():
    s, bus = S.search, S.bus

    if not S.seats:
        return go("seats")

    res = service.reserved(bus["rows"])

    st.subheader("Passenger details")

    st.markdown(
        f'<div class="card">'
        f'{bus["operator"]} · {s["src"]} → {s["dst"]} · {s["date"]:%d %b}<br>'
        f'Seats {", ".join(S.seats)} · '
        f'<b>{money(service.fare(bus["price"], len(S.seats))["base"])}</b>'
        f'</div>',
        unsafe_allow_html=True
    )

    with st.form("passenger_form"):
        data = []

        for i, seat in enumerate(S.seats):
            st.markdown(f"**Passenger {i + 1} · Seat {seat}**")

            a, b = st.columns(2)

            name = a.text_input(
                "Full name",
                key=f"pn{i}",
                value=S.user["name"] if i == 0 else ""
            )

            age = b.number_input(
                "Age",
                min_value=1,
                max_value=100,
                value=25,
                key=f"pa{i}"
            )

            c, d = st.columns(2)

            gender = c.selectbox(
                "Gender",
                ["Male", "Female", "Other"],
                key=f"pg{i}"
            )

            phone = d.text_input(
                "Mobile",
                key=f"pm{i}",
                value=S.user["phone"] if i == 0 else ""
            )

            email = st.text_input(
                "Email",
                key=f"pe{i}",
                value=S.user["email"] if i == 0 else ""
            )

            data.append({
                "name": name.strip(),
                "age": int(age),
                "gender": gender,
                "phone": phone,
                "email": email,
                "seat": seat
            })

        submitted = st.form_submit_button(
            "Proceed to Payment",
            type="primary",
            use_container_width=True
        )

        if submitted:
            err = None

            for p in data:
                if len(p["name"]) < 2:
                    err = "Enter every passenger's name."

                elif not re.fullmatch(r"\d{10}", p["phone"]):
                    err = "Mobile must be 10 digits."

                elif not re.match(r"[^@]+@[^@]+\.\w+", p["email"]):
                    err = "Enter a valid email."

                elif res.get(p["seat"]) == "F" and p["gender"] != "Female":
                    err = f"Seat {p['seat']} is reserved for ladies."

                elif res.get(p["seat"]) == "M" and p["gender"] != "Male":
                    err = f"Seat {p['seat']} is reserved for gents."

                if err:
                    break

            if err:
                st.error(err)
            else:
                S.pax = data
                go("payment")

    if st.button("← Back"):
        go("seats")


def payment():
    s, bus = S.search, S.bus
    if not S.pax: return go("passengers")
    st.subheader("Payment")
    S.promo = st.text_input("Promo code (BUSGO10 / WELCOME50)", S.promo)
    f = service.fare(bus["price"], len(S.seats), S.promo)
    if S.promo and f["discount"] == 0: st.warning("Invalid promo code.")
    st.markdown(f'<div class="card">Base fare: {money(f["base"])}<br>Taxes (5%): {money(f["taxes"])}<br>'
                f'Convenience fee: {money(f["fee"])}<br>Discount: −{money(f["discount"])}<br>'
                f'<b>Total: <span class="price">{money(f["total"])}</span></b></div>', unsafe_allow_html=True)
    m = st.radio("Method", ["UPI", "Credit/Debit Card", "Net Banking", "Wallet"], horizontal=True)
    ok = True
    if m == "UPI":
        ok = bool(re.fullmatch(r"[\w.\-]+@[\w]+", st.text_input("UPI ID", placeholder="name@upi")))
    elif m == "Credit/Debit Card":
        st.text_input("Card number", placeholder="4111 1111 1111 1111"); a, b = st.columns(2)
        a.text_input("Expiry (MM/YY)"); b.text_input("CVV", type="password")
    elif m == "Net Banking": st.selectbox("Bank", ["HDFC", "SBI", "ICICI", "Axis"])
    else: st.selectbox("Wallet", ["Paytm", "PhonePe", "Amazon Pay"])
    st.caption("🔒 Mock payment – no real money is processed.")
    if st.button(f"Pay Now · {money(f['total'])}", type="primary", use_container_width=True):
        if not ok: st.error("Enter a valid UPI ID."); return
        with st.spinner("Processing payment…"): time.sleep(1.2)
        bid = service.create_booking(S.user["id"], bus["id"], s["date"], S.pax, S.seats, f, m)
        if not bid: st.error("Sorry, a seat was just taken. Please reselect."); return
        S.booking = bid; S.promo = ""; go("confirm")
    if st.button("← Back"): go("passengers")


def ticket_html(b):
    pax = json.loads(b["passengers"])
    rows = "".join(f"<tr><td>{p['name']}</td><td>{p['age']}/{p['gender']}</td><td>{p['seat']}</td></tr>" for p in pax)
    return f"""<html><body style="font-family:Arial;max-width:520px;margin:auto;border:2px dashed #4F46E5;padding:20px">
<h2 style="color:#4F46E5">🚌 BusGo E-Ticket</h2><p><b>Booking ID:</b> {b['id']} &nbsp; <b>Status:</b> {b['status']}</p>
<p><b>{b['operator']}</b> ({b['bus_type']}, {b['number']})</p>
<h3>{b['src']} → {b['dst']}</h3><p>Date: {b['journey_date']} · Departure {b['dep']} · Arrival {b['arr']}</p>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%"><tr><th>Passenger</th><th>Age/Gender</th><th>Seat</th></tr>{rows}</table>
<h3>Total paid: ₹{b['total']:,.2f}</h3><p style="color:#666">Show this ticket at boarding. Have a safe journey!</p></body></html>"""


def show_ticket(bid, key=""):
    b = service.get_booking(bid)
    pax = json.loads(b["passengers"])
    st.markdown(f'<div class="card"><span class="chip">{b["id"]}</span> <b>{b["operator"]}</b><br>'
                f'{b["src"]} → {b["dst"]} · {b["journey_date"]} · {b["dep"]}<br>'
                f'Seats: {", ".join(json.loads(b["seats"]))} · Total {money(b["total"])}</div>', unsafe_allow_html=True)
    for p in pax: st.write(f"👤 {p['name']} ({p['age']}, {p['gender']}) — seat {p['seat']}")
    st.download_button("⬇️ Download Ticket", ticket_html(b), f"ticket_{bid}.html", "text/html", key=f"dl{key}{bid}")


def confirm():
    if not S.booking: return go("home")
    st.markdown('<div class="ok">✅</div>', unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center'>Booking Confirmed</h2>", unsafe_allow_html=True)
    st.balloons() if not S.get("_b") else None; S["_b"] = True
    show_ticket(S.booking, "c")
    a, b = st.columns(2)
    if a.button("View Booking", use_container_width=True): S._b = False; go("bookings")
    if b.button("Go to Home", use_container_width=True): S._b = False; go("home")


def bookings():
    st.subheader("My Bookings")
    allb = service.bookings_of(S.user["id"])
    tabs = st.tabs(["Upcoming", "Completed", "Cancelled"])
    for tab, name in zip(tabs, ["Upcoming", "Completed", "Cancelled"]):
        with tab:
            items = [b for b in allb if service.group(b) == name]
            if not items: st.info(f"No {name.lower()} bookings.")
            for b in items:
                with st.container(border=True):
                    st.markdown(f"**{b['src']} → {b['dst']}** · {b['operator']}  \n"
                                f"`{b['id']}` · {b['journey_date']} {b['dep']} · Seats {', '.join(json.loads(b['seats']))} · "
                                f"{money(b['total'])} · **{b['status']}**")
                    c1, c2 = st.columns(2)
                    if c1.button("View Ticket", key=f"vt{b['id']}"): S[f"show{b['id']}"] = not S.get(f"show{b['id']}")
                    if name == "Upcoming" and c2.button("Cancel Booking", key=f"cb{b['id']}"): S.cancel = b["id"]
                    if S.get(f"show{b['id']}"): show_ticket(b["id"], "l")
    if S.get("cancel"):
        @st.dialog("Cancel this booking?")
        def dlg():
            st.write(f"Booking **{S.cancel}** will be cancelled and refunded.")
            a, b = st.columns(2)
            if a.button("Yes, cancel", type="primary"):
                service.cancel_booking(S.cancel); S.cancel = None; st.toast("Booking cancelled"); st.rerun()
            if b.button("Keep it"): S.cancel = None; st.rerun()
        dlg()


def profile():
    u = S.user
    st.subheader("Profile")
    st.markdown(f'<div class="card" style="text-align:center"><div style="font-size:56px">🧑</div><b>{u["name"]}</b><br>'
                f'{u["email"]}<br>{u["phone"]}</div>', unsafe_allow_html=True)
    with st.expander("✏️ Edit Profile"):
        with st.form("ep"):
            n = st.text_input("Name", u["name"]); p = st.text_input("Mobile", u["phone"])
            if st.form_submit_button("Save") and len(n) > 1 and re.fullmatch(r"\d{10}", p):
                service.update_profile(u["id"], n, p); S.user.update(name=n, phone=p); st.success("Saved"); st.rerun()
    for label, txt in [("👥 Saved Passengers", "Passengers you book for are stored with each booking."),
                       ("🔔 Notifications", "No new notifications."), ("💳 Payment Methods", "UPI, Cards, Net Banking, Wallet (mock)."),
                       ("❓ Help & Support", "support@busgo.example"), ("📄 Terms & Conditions", "Demo application terms."),
                       ("🔐 Privacy Policy", "Passwords are salted & hashed. Demo only.")]:
        with st.expander(label): st.write(txt)
    if st.button("My Bookings", use_container_width=True): go("bookings")
    if st.button("Logout", type="primary", use_container_width=True):
        for k in list(S.keys()): del S[k]
        st.rerun()


# ================= ADMIN =================
def admin():
    st.subheader("🛠️ Admin Panel")
    t = st.tabs(["Dashboard", "Buses", "Routes", "Bookings", "Users", "Reports"])
    with t[0]:
        s = service.stats()
        c = st.columns(3)
        c[0].metric("Total buses", s["buses"]); c[1].metric("Users", s["users"]); c[2].metric("Today's bookings", s["today"])
        c = st.columns(2)
        c[0].metric("Revenue", money(s["revenue"])); c[1].metric("Total seats", s["seats"])
        d = service.df("SELECT substr(created,1,10) day, COUNT(*) bookings, SUM(total) revenue FROM bookings WHERE status='Confirmed' GROUP BY day")
        if d.empty: st.info("No bookings yet – charts appear after the first booking.")
        else:
            st.markdown("**Daily bookings**"); st.bar_chart(d.set_index("day")["bookings"])
            d["month"] = d["day"].str[:7]
            st.markdown("**Monthly revenue**"); st.line_chart(d.groupby("month")["revenue"].sum())
            p = service.df("SELECT s.src||' → '||s.dst route, COUNT(*) n FROM bookings b JOIN buses s ON s.id=b.bus_id "
                      "WHERE b.status='Confirmed' GROUP BY route ORDER BY n DESC")
            st.markdown("**Popular routes**"); st.bar_chart(p.set_index("route"))
    with t[1]:
        cities = service.cities()
        buses = service.df("SELECT * FROM buses ORDER BY id")
        st.dataframe(buses, use_container_width=True, hide_index=True)
        mode = st.radio("Action", ["Add bus", "Edit bus", "Delete bus"], horizontal=True)
        row = None
        if mode != "Add bus":
            bid = st.selectbox("Bus", buses.id, format_func=lambda i: f"#{i} {buses[buses.id==i].operator.iloc[0]} "
                               f"{buses[buses.id==i].src.iloc[0]}→{buses[buses.id==i].dst.iloc[0]} {buses[buses.id==i].dep.iloc[0]}")
            row = buses[buses.id == bid].iloc[0]
        if mode == "Delete bus":
            if st.button("Delete", type="primary"): service.delete_bus(int(bid)); st.rerun()
        else:
            g = lambda k, dflt: row[k] if row is not None else dflt
            tm = lambda s: datetime.strptime(s, "%H:%M").time()
            with st.form(f"bus{mode}"):
                a, b = st.columns(2)
                op = a.text_input("Operator", g("operator", "")); num = b.text_input("Bus number", g("number", ""))
                bt = a.text_input("Bus type", g("bus_type", "Volvo")); kind = b.selectbox("Seat kind", ["Seater", "Sleeper"],
                                                                                          index=["Seater", "Sleeper"].index(g("seat_kind", "Seater")))
                src = a.selectbox("From", cities, index=cities.index(g("src", cities[0])))
                dst = b.selectbox("To", cities, index=cities.index(g("dst", cities[1])))
                dep = a.time_input("Departure", tm(g("dep", "08:00"))); arr = b.time_input("Arrival", tm(g("arr", "12:00")))
                price = a.number_input("Price (₹)", 50.0, 10000.0, float(g("price", 500)))
                rows = b.number_input("Seat rows (×4 seats)", 3, 20, int(g("rows", 10)))
                ac = a.checkbox("AC", bool(g("ac", 1))); rating = b.number_input("Rating", 1.0, 5.0, float(g("rating", 4.0)))
                if st.form_submit_button("Save", type="primary"):
                    if not op or not num or src == dst: st.error("Fill operator, number and distinct cities.")
                    else:
                        service.save_bus(dict(operator=op, number=num, bus_type=bt, ac=int(ac), seat_kind=kind, src=src, dst=dst,
                                         dep=dep.strftime("%H:%M"), arr=arr.strftime("%H:%M"), price=price, rows=int(rows),
                                         rating=rating), int(row["id"]) if row is not None else None)
                        st.success("Saved"); st.rerun()
    with t[2]:
        r = service.df("SELECT * FROM routes")
        st.dataframe(r, use_container_width=True, hide_index=True)
        with st.form("rt"):
            a, b, c = st.columns(3)
            s_ = a.text_input("From"); d_ = b.text_input("To"); k = c.number_input("Distance (km)", 1.0, 3000.0, 100.0)
            if st.form_submit_button("Add route") and s_ and d_ and s_ != d_:
                service.save_route(s_.strip().title(), d_.strip().title(), k); st.rerun()
        if not r.empty:
            rid = st.selectbox("Delete route", r.id, format_func=lambda i: f"{r[r.id==i].src.iloc[0]} → {r[r.id==i].dst.iloc[0]}")
            if st.button("Delete route"): service.delete_route(int(rid)); st.rerun()
    with t[3]:
        bk = service.bookings_of()
        if not bk: st.info("No bookings yet.")
        for b in bk:
            with st.container(border=True):
                st.write(f"`{b['id']}` · {b['user_name']} · {b['src']}→{b['dst']} · {b['journey_date']} · "
                         f"{money(b['total'])} · **{b['status']}**")
                if b["status"] == "Confirmed" and st.button("Cancel", key=f"ac{b['id']}"):
                    service.cancel_booking(b["id"]); st.rerun()
    with t[4]:
        st.dataframe(service.df("SELECT id,name,email,phone,role FROM users"), use_container_width=True, hide_index=True)
    with t[5]:
        rep = service.df("SELECT b.id, u.name, s.operator, s.src, s.dst, b.journey_date, b.total, b.status FROM bookings b "
                    "JOIN users u ON u.id=b.user_id JOIN buses s ON s.id=b.bus_id")
        st.dataframe(rep, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export CSV", rep.to_csv(index=False), "report.csv", "text/csv")


# ================= ROUTER =================
if not S.user:
    auth_page(); st.stop()

with st.sidebar:
    st.markdown("## 🚌 BusGo")
    st.caption(f"{S.user['name']} · {S.user['role']}")
    nav = [("🏠 Home", "home"), ("🎫 My Bookings", "bookings"), ("👤 Profile", "profile")]
    if S.user["role"] == "admin": nav.append(("🛠️ Admin", "admin"))
    for label, p in nav:
        if st.button(label, use_container_width=True, key=f"n{p}"): S.page = p; st.rerun()

{"home": home, "results": results, "seats": seats, "passengers": passengers, "payment": payment,
 "confirm": confirm, "bookings": bookings, "profile": profile,
 "admin": admin if S.user["role"] == "admin" else home}[S.page]()
