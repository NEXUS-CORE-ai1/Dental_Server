from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from datetime import datetime

app = FastAPI()

def init_db():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    
    # Valyuta kursi jadvali (Boshlang'ich 1 USD = 12800 UZS)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('usd_rate', 12800.0)")
    
    # Foydalanuvchilar
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('user', 'user123', 'registratura')")
    
    # Ish turlari va narxi (USD da)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price_usd REAL NOT NULL
        )
    ''')
    
    # Mijozlar bazasi (Asosiy balans USD da)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            balance_usd REAL DEFAULT 0.0
        )
    ''')
    
    # Buyurtmalar (Barcha hisob-kitoblar USD da, kurs saqlanadi)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            service_name TEXT,
            unit_count INTEGER,
            total_usd REAL,
            total_uzs REAL,
            usd_rate REAL,
            created_at TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'Qabul qilindi',
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    ''')
    
    # To'lovlar tarixi (UZS da berilgan pul izi saqlanadi)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            amount_uzs REAL,
            amount_usd REAL,
            usd_rate REAL,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# --- Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

class RateUpdate(BaseModel):
    usd_rate: float

class ServiceCreate(BaseModel):
    name: str
    price_usd: float

class ClientCreate(BaseModel):
    name: str
    phone: str

class OrderCreate(BaseModel):
    client_id: int
    service_name: str
    unit_count: int
    total_usd: float
    total_uzs: float
    usd_rate: float
    deadline: str

class PaymentCreate(BaseModel):
    client_id: int
    amount_uzs: float
    usd_rate: float

# --- Endpoints ---
@app.post("/login/")
def login(req: LoginRequest):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, role FROM users WHERE username = ? AND password = ?", (req.username, req.password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"status": "ok", "username": user[0], "role": user[1]}
    raise HTTPException(status_code=401, detail="Xato login/parol")

# --- Kurs boshqaruvi ---
@app.get("/rate/")
def get_rate():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'usd_rate'")
    rate = cursor.fetchone()[0]
    conn.close()
    return {"usd_rate": rate}

@app.post("/rate/")
def update_rate(rate: RateUpdate):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value = ? WHERE key = 'usd_rate'", (rate.usd_rate,))
    conn.commit()
    conn.close()
    return {"message": "Valyuta kursi yangilandi"}

# --- Users boshqaruvi ---
@app.get("/users/")
def get_users():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM users")
    users = cursor.fetchall()
    conn.close()
    return [{"id": u[0], "username": u[1], "role": u[2]} for u in users]

@app.post("/users/")
def add_user(user: UserCreate):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                       (user.username, user.password, user.role))
        conn.commit()
    except:
        conn.close()
        raise HTTPException(status_code=400, detail="Bunday loginli foydalanuvchi mavjud")
    conn.close()
    return {"message": "Foydalanuvchi qo'shildi"}

# --- Services, Clients, Orders & Payments ---
@app.post("/services/")
def add_service(service: ServiceCreate):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO services (name, price_usd) VALUES (?, ?)", (service.name, service.price_usd))
    conn.commit()
    conn.close()
    return {"message": "Ish turi qo'shildi"}

@app.get("/services/")
def get_services():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price_usd FROM services")
    services = cursor.fetchall()
    conn.close()
    return [{"id": s[0], "name": s[1], "price_usd": s[2]} for s in services]

@app.post("/clients/")
def add_client(client: ClientCreate):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO clients (name, phone) VALUES (?, ?)", (client.name, client.phone))
    conn.commit()
    conn.close()
    return {"message": "Mijoz qo'shildi"}

@app.get("/clients/")
def get_clients():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone, balance_usd FROM clients")
    clients = cursor.fetchall()
    conn.close()
    return [{"id": c[0], "name": c[1], "phone": c[2], "balance_usd": c[3]} for c in clients]

@app.post("/orders/")
def create_order(order: OrderCreate):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    cursor.execute('''
        INSERT INTO orders (client_id, service_name, unit_count, total_usd, total_uzs, usd_rate, created_at, deadline)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (order.client_id, order.service_name, order.unit_count, order.total_usd, order.total_uzs, order.usd_rate, created_at, order.deadline))
    
    cursor.execute("UPDATE clients SET balance_usd = balance_usd + ? WHERE id = ?", (order.total_usd, order.client_id))
    
    conn.commit()
    conn.close()
    return {"message": "Buyurtma saqlandi"}

@app.get("/orders/")
def get_orders():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT orders.id, clients.name, orders.service_name, orders.unit_count, 
               orders.total_usd, orders.total_uzs, orders.usd_rate, orders.created_at, orders.deadline, orders.status
        FROM orders
        JOIN clients ON orders.client_id = clients.id
        ORDER BY orders.id DESC
    ''')
    orders = cursor.fetchall()
    conn.close()
    return orders

@app.post("/payments/")
def make_payment(payment: PaymentCreate):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    amount_usd = payment.amount_uzs / payment.usd_rate
    
    cursor.execute('''
        INSERT INTO payments (client_id, amount_uzs, amount_usd, usd_rate, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (payment.client_id, payment.amount_uzs, amount_usd, payment.usd_rate, created_at))
    
    # Balansdan qarzni ayirish
    cursor.execute("UPDATE clients SET balance_usd = balance_usd - ? WHERE id = ?", (amount_usd, payment.client_id))
    
    conn.commit()
    conn.close()
    return {"message": "To'lov qabul qilindi"}