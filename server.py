from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from datetime import datetime

app = FastAPI()

def init_db():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    
    # 1. Filiallar
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO branches (id, name) VALUES (1, 'Bosh Filial')")
    
    # 2. Sozlamalar (USD Kursi)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('usd_rate', 12800.0)")
    
    # 3. Foydalanuvchilar (Filialga bog'langan)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            branch_id INTEGER,
            FOREIGN KEY(branch_id) REFERENCES branches(id)
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role, branch_id) VALUES ('admin', 'admin123', 'admin', 1)")
    
    # 4. Ish turlari
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price_usd REAL NOT NULL
        )
    ''')
    
    # 5. Mijozlar (User va Filialga bog'liq, Admin ruxsati bayrog'i bilan)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            balance_usd REAL DEFAULT 0.0,
            created_by_user_id INTEGER,
            branch_id INTEGER,
            is_public_to_all INTEGER DEFAULT 0,
            FOREIGN KEY(created_by_user_id) REFERENCES users(id),
            FOREIGN KEY(branch_id) REFERENCES branches(id)
        )
    ''')
    
    # 6. Buyurtmalar
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            user_id INTEGER,
            branch_id INTEGER,
            service_name TEXT,
            unit_count INTEGER,
            total_usd REAL,
            total_uzs REAL,
            usd_rate REAL,
            created_at TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'Qabul qilindi',
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(branch_id) REFERENCES branches(id)
        )
    ''')
    
    # 7. To'lovlar
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            user_id INTEGER,
            branch_id INTEGER,
            amount_uzs REAL,
            amount_usd REAL,
            usd_rate REAL,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(branch_id) REFERENCES branches(id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# --- SCHEMAS ---
class LoginReq(BaseModel):
    username: str
    password: str

class UserReq(BaseModel):
    username: str
    password: str
    role: str
    branch_id: int

class BranchReq(BaseModel):
    name: str

class RateReq(BaseModel):
    usd_rate: float

class ServiceReq(BaseModel):
    name: str
    price_usd: float

class ClientReq(BaseModel):
    name: str
    phone: str
    user_id: int
    branch_id: int

class ClientVisibilityReq(BaseModel):
    client_id: int
    is_public: int

class OrderReq(BaseModel):
    client_id: int
    user_id: int
    branch_id: int
    service_name: str
    unit_count: int
    total_usd: float
    total_uzs: float
    usd_rate: float
    deadline: str

class PaymentReq(BaseModel):
    client_id: int
    user_id: int
    branch_id: int
    amount_uzs: float
    usd_rate: float

# --- ENDPOINTS ---
@app.post("/login/")
def login(req: LoginReq):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, branch_id FROM users WHERE username = ? AND password = ?", (req.username, req.password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"status": "ok", "user_id": user[0], "username": user[1], "role": user[2], "branch_id": user[3]}
    raise HTTPException(status_code=401, detail="Xato login/parol")

# Filiallar
@app.get("/branches/")
def get_branches():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM branches")
    b = cursor.fetchall()
    conn.close()
    return [{"id": i[0], "name": i[1]} for i in b]

@app.post("/branches/")
def add_branch(req: BranchReq):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO branches (name) VALUES (?)", (req.name,))
        conn.commit()
    except:
        conn.close()
        raise HTTPException(status_code=400, detail="Bunday filial mavjud")
    conn.close()
    return {"message": "Filial qo'shildi"}

# Kurs va Sozlamalar
@app.get("/rate/")
def get_rate():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'usd_rate'")
    rate = cursor.fetchone()[0]
    conn.close()
    return {"usd_rate": rate}

@app.post("/rate/")
def update_rate(req: RateReq):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value = ? WHERE key = 'usd_rate'", (req.usd_rate,))
    conn.commit()
    conn.close()
    return {"message": "Kurs yangilandi"}

# Foydalanuvchilar
@app.get("/users/")
def get_users():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT users.id, users.username, users.role, branches.name 
        FROM users 
        LEFT JOIN branches ON users.branch_id = branches.id
    ''')
    users = cursor.fetchall()
    conn.close()
    return [{"id": u[0], "username": u[1], "role": u[2], "branch_name": u[3]} for u in users]

@app.post("/users/")
def add_user(req: UserReq):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, role, branch_id) VALUES (?, ?, ?, ?)", 
                       (req.username, req.password, req.role, req.branch_id))
        conn.commit()
    except:
        conn.close()
        raise HTTPException(status_code=400, detail="Bunday login mavjud")
    conn.close()
    return {"message": "User yaratildi"}

# Ish Turlari
@app.get("/services/")
def get_services():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price_usd FROM services")
    s = cursor.fetchall()
    conn.close()
    return [{"id": i[0], "name": i[1], "price_usd": i[2]} for i in s]

@app.post("/services/")
def add_service(req: ServiceReq):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO services (name, price_usd) VALUES (?, ?)", (req.name, req.price_usd))
    conn.commit()
    conn.close()
    return {"message": "Ish qo'shildi"}

# Mijozlar (Filial va Ruxsatlar Filtrlari Bilan)
@app.get("/clients/")
def get_clients(user_id: int, role: str, branch_id: int):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    
    if role == "admin":
        cursor.execute('''
            SELECT clients.id, clients.name, clients.phone, clients.balance_usd, 
                   users.username, branches.name, clients.is_public_to_all
            FROM clients
            LEFT JOIN users ON clients.created_by_user_id = users.id
            LEFT JOIN branches ON clients.branch_id = branches.id
        ''')
    else:
        # Bir xil filialdagi userlarga hamda admin ommaviy qilgan mijozlarga ko'rinadi
        cursor.execute('''
            SELECT clients.id, clients.name, clients.phone, clients.balance_usd, 
                   users.username, branches.name, clients.is_public_to_all
            FROM clients
            LEFT JOIN users ON clients.created_by_user_id = users.id
            LEFT JOIN branches ON clients.branch_id = branches.id
            WHERE clients.branch_id = ? OR clients.is_public_to_all = 1
        ''', (branch_id,))
        
    c = cursor.fetchall()
    conn.close()
    return [{"id": i[0], "name": i[1], "phone": i[2], "balance_usd": i[3], 
             "created_by": i[4], "branch": i[5], "is_public": i[6]} for i in c]

@app.post("/clients/")
def add_client(req: ClientReq):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO clients (name, phone, created_by_user_id, branch_id) 
        VALUES (?, ?, ?, ?)
    ''', (req.name, req.phone, req.user_id, req.branch_id))
    conn.commit()
    conn.close()
    return {"message": "Mijoz muvaffaqiyatli qo'shildi"}

@app.post("/clients/visibility/")
def set_visibility(req: ClientVisibilityReq):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET is_public_to_all = ? WHERE id = ?", (req.is_public, req.client_id))
    conn.commit()
    conn.close()
    return {"message": "Mijoz ruxsati o'zgartirildi"}

# Buyurtmalar
@app.get("/orders/")
def get_orders(role: str, branch_id: int):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    if role == "admin":
        cursor.execute('''
            SELECT orders.id, clients.name, orders.service_name, orders.unit_count, 
                   orders.total_usd, orders.total_uzs, branches.name, orders.created_at, orders.deadline
            FROM orders
            JOIN clients ON orders.client_id = clients.id
            LEFT JOIN branches ON orders.branch_id = branches.id
            ORDER BY orders.id DESC
        ''')
    else:
        cursor.execute('''
            SELECT orders.id, clients.name, orders.service_name, orders.unit_count, 
                   orders.total_usd, orders.total_uzs, branches.name, orders.created_at, orders.deadline
            FROM orders
            JOIN clients ON orders.client_id = clients.id
            LEFT JOIN branches ON orders.branch_id = branches.id
            WHERE orders.branch_id = ?
            ORDER BY orders.id DESC
        ''', (branch_id,))
    o = cursor.fetchall()
    conn.close()
    return o

@app.post("/orders/")
def create_order(req: OrderReq):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute('''
        INSERT INTO orders (client_id, user_id, branch_id, service_name, unit_count, total_usd, total_uzs, usd_rate, created_at, deadline)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (req.client_id, req.user_id, req.branch_id, req.service_name, req.unit_count, req.total_usd, req.total_uzs, req.usd_rate, created_at, req.deadline))
    
    cursor.execute("UPDATE clients SET balance_usd = balance_usd + ? WHERE id = ?", (req.total_usd, req.client_id))
    conn.commit()
    conn.close()
    return {"message": "Buyurtma saqlandi"}

@app.post("/payments/")
def make_payment(req: PaymentReq):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    amount_usd = req.amount_uzs / req.usd_rate
    
    cursor.execute('''
        INSERT INTO payments (client_id, user_id, branch_id, amount_uzs, amount_usd, usd_rate, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (req.client_id, req.user_id, req.branch_id, req.amount_uzs, amount_usd, req.usd_rate, created_at))
    
    cursor.execute("UPDATE clients SET balance_usd = balance_usd - ? WHERE id = ?", (amount_usd, req.client_id))
    conn.commit()
    conn.close()
    return {"message": "To'lov qabul qilindi"}

# HISOBOTLAR BO'LIMI (Filial va Userlar Kesimida)
@app.get("/reports/")
def get_reports(branch_id: int = None):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    
    if branch_id and branch_id > 0:
        cursor.execute("SELECT SUM(total_usd), SUM(total_uzs) FROM orders WHERE branch_id = ?", (branch_id,))
        orders_stat = cursor.fetchone()
        cursor.execute("SELECT SUM(amount_usd), SUM(amount_uzs) FROM payments WHERE branch_id = ?", (branch_id,))
        payments_stat = cursor.fetchone()
    else:
        cursor.execute("SELECT SUM(total_usd), SUM(total_uzs) FROM orders")
        orders_stat = cursor.fetchone()
        cursor.execute("SELECT SUM(amount_usd), SUM(amount_uzs) FROM payments")
        payments_stat = cursor.fetchone()
        
    conn.close()
    return {
        "total_orders_usd": orders_stat[0] or 0.0,
        "total_orders_uzs": orders_stat[1] or 0.0,
        "total_payments_usd": payments_stat[0] or 0.0,
        "total_payments_uzs": payments_stat[1] or 0.0
    }