"""Customers (all FICTIONAL): export distributors across ~20 markets, domestic OEMs, dealers and institutional projects.
Segment drives the order class (export / committed domestic / open domestic) and which SKUs the customer buys."""
from .common import R, rint

EXPORT = [
    ("Al Safa Interiors LLC", "UAE", "Dubai"), ("Gulf Panel Trading LLC", "UAE", "Sharjah"), ("Desert Rose Furnishings FZE", "UAE", "Ras Al Khaimah"),
    ("Najd Board & Decor Co.", "Saudi Arabia", "Riyadh"), ("Pearl Coast Fitout WLL", "Qatar", "Doha"), ("Muscat Surfaces LLC", "Oman", "Muscat"),
    ("Mombasa Board House Ltd", "Kenya", "Mombasa"), ("Kilimanjaro Panels Ltd", "Tanzania", "Dar es Salaam"), ("Lagos Laminate Mart Ltd", "Nigeria", "Lagos"),
    ("Kestrel Surfaces Ltd", "United Kingdom", "Manchester"), ("Thames Panel Supplies Ltd", "United Kingdom", "London"),
    ("Nordlicht Plattenhandel GmbH", "Germany", "Hamburg"), ("Baltic Decor Sp. z o.o.", "Poland", "Gdansk"),
    ("Harbour Board Supplies Pty Ltd", "Australia", "Sydney"), ("Southern Cross Laminates Pty", "Australia", "Melbourne"),
    ("Kiwi Joinery Supplies Ltd", "New Zealand", "Auckland"), ("Lakeside Panel Co.", "United States", "Chicago"),
    ("Ceylon Board House (Pvt) Ltd", "Sri Lanka", "Colombo"), ("Himalaya Laminates Traders", "Nepal", "Kathmandu"),
    ("Padma Furnish Mart", "Bangladesh", "Dhaka"), ("Saigon Panel JSC", "Vietnam", "Ho Chi Minh City"), ("Nusantara Board PT", "Indonesia", "Jakarta"),
    ("Klang Valley Surfaces Sdn Bhd", "Malaysia", "Kuala Lumpur"), ("Nile Decor Panels SAE", "Egypt", "Cairo"), ("Island Fitout Ltd", "Mauritius", "Port Louis"),
]
OEM = [
    ("Urban Nest Modular Kitchens", "Bengaluru"), ("Kaveri Office Systems", "Chennai"), ("Ashoka Furniture Works", "Delhi"), ("Sahyadri Modular", "Pune"),
    ("Coastline Wardrobes", "Kochi"), ("Metro Workspace Interiors", "Gurugram"), ("Deccan Doors & Shutters", "Hyderabad"), ("Aravali Kitchen Studio", "Jaipur"),
    ("Ganga Furniture Industries", "Kanpur"), ("Narmada Office Furniture", "Indore"), ("Hooghly Interiors", "Kolkata"), ("Sabarmati Modular", "Ahmedabad"),
    ("Konark Furnishers", "Bhubaneswar"), ("Malabar Home Systems", "Kozhikode"), ("Vindhya Panel Craft", "Bhopal"),
]
DEALER_NAMES = ["Shree Balaji", "Jai Ambe", "Laxmi", "Krishna", "Sai Kripa", "Om Sai", "Mahalaxmi", "New India", "Royal", "Patel", "Agarwal", "Gupta",
                "Sharma", "Mehta", "Kapoor", "Bansal", "Singhal", "Jain", "Reddy", "Nair", "Iyer", "Desai", "Chawla", "Arora", "Malhotra", "Saxena",
                "Tiwari", "Pandey", "Joshi", "Rao"]
DEALER_KIND = ["Plywood & Laminates", "Decor House", "Laminate Centre", "Hardware & Laminates", "Interior Mart"]
DEALER_CITY = ["Lucknow", "Patna", "Nagpur", "Surat", "Vadodara", "Ludhiana", "Chandigarh", "Dehradun", "Raipur", "Ranchi", "Guwahati", "Coimbatore",
               "Madurai", "Vijayawada", "Visakhapatnam", "Mysuru", "Mangaluru", "Nashik", "Aurangabad", "Rajkot", "Jodhpur", "Udaipur", "Agra",
               "Varanasi", "Meerut", "Jammu", "Amritsar", "Thiruvananthapuram", "Hubballi", "Siliguri"]
PROJECTS = [
    ("City Care Hospital Project", "Noida", "AB CR"), ("Metro Rail Coach Interiors", "Chennai", "FR"), ("State Science College Labs", "Lucknow", "CR"),
    ("Airport Terminal 3 Fitout", "Bengaluru", "FR"), ("IT Park Tower B Fitout", "Hyderabad", "GP FR"), ("Grand Residency Hotel Refurb", "Goa", "GP AB"),
    ("University Hostel Block C", "Pune", "GP CP"), ("Government Medical College Labs", "Jaipur", "CR AB"), ("Smart City Bus Shelters", "Indore", "EX"),
    ("Railway Station Redevelopment", "Ahmedabad", "FR EX"),
]
# a customer's texture always comes from one mould set on one press (req 1c): (customer name, finish, bed ft, press)
DEDICATED = [
    ("Harbour Board Supplies Pty Ltd", "OP", 14, "P4"), ("Kestrel Surfaces Ltd", "SM", 8, "P1"), ("Al Safa Interiors LLC", "HG", 16, "P6"),
    ("Urban Nest Modular Kitchens", "SU", 8, "P3"), ("Kaveri Office Systems", "TL", 14, "P5"), ("Nordlicht Plattenhandel GmbH", "SY", 8, "P2"),
    ("Southern Cross Laminates Pty", "AG", 8, "P1"), ("Lakeside Panel Co.", "WP", 14, "P4"),
]


def build_customers():
    out = []
    n = 0

    def add(**kw):
        nonlocal n
        n += 1
        kw["id"] = "C%03d" % n
        out.append(kw)
        return kw

    for name, country, city in EXPORT:
        add(name=name, segment="EXPORT", country=country, city=city, creditDays=rint(30, 90), keyAccount=name in [d[0] for d in DEDICATED], grades="GP EX")
    for name, city in OEM:
        add(name=name, segment="OEM", country="India", city=city, creditDays=rint(30, 60), keyAccount=name in [d[0] for d in DEDICATED], grades="GP PF")
    used = set()
    for i in range(30):
        nm = "%s %s" % (DEALER_NAMES[i], DEALER_KIND[i % len(DEALER_KIND)])
        city = DEALER_CITY[i]
        while nm in used:
            nm += " II"
        used.add(nm)
        add(name=nm, segment="DEALER", country="India", city=city, creditDays=rint(15, 45), keyAccount=False, grades="GP PF")
    for name, city, grades in PROJECTS:
        add(name=name, segment="PROJECT", country="India", city=city, creditDays=rint(45, 90), keyAccount=False, grades=grades)
    return out


def dedicated_pairs(customers):
    by_name = {c["name"]: c["id"] for c in customers}
    return [(by_name[n], fin, bed, pid) for n, fin, bed, pid in DEDICATED]
