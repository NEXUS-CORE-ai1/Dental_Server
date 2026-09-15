from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from datetime import datetime

app = FastAPI()

def init_db():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    
    # Foydalanuvchilar (Login/Parol va Rol)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # Ish turlari va narxlari (USD / UZS)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            currency TEXT NOT NULL
        )
    ''')
    
    # Mijozlar
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            balance_uzs REAL DEFAULT 0.0,
            balance_usd REAL DEFAULT 0.0
        )
    ''')
    
    # Buyurtmalar
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            service_name TEXT,
            unit_count INTEGER,
            total_price REAL,
            currency TEXT,
            created_at TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'Qabul qilindi',
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    ''')
    
    # Boshlang'ich Admin va Registrator akkauntlarini yaratish
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
        cursor.execute("INSERT INTO users (username, password, role) VALUES ('user', 'user123', 'registratura')")
    
    conn.commit()
    conn.close()

init_db()

# --- Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str

class ServiceCreate(BaseModel):
    name: str
    price: float
    currency: str

class ClientCreate(BaseModel):
    name: str
    phone: str

class OrderCreate(BaseModel):
    client_id: int
    service_name: str
    unit_count: int
    total_price: float
    currency: str
    deadline: str

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
    raise HTTPException(status_code=401, detail="Login yoki parol noto'g'ri")

@app.post("/services/")
def add_service(service: ServiceCreate):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO services (name, price, currency) VALUES (?, ?, ?)", 
                   (service.name, service.price, service.currency))
    conn.commit()
    conn.close()
    return {"message": "Ish turi qo'shildi"}

@app.get("/services/")
def get_services():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, currency FROM services")
    services = cursor.fetchall()
    conn.close()
    return [{"id": s[0], "name": s[1], "price": s[2], "currency": s[3]} for s in services]

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
    cursor.execute("SELECT id, name, phone, balance_uzs, balance_usd FROM clients")
    clients = cursor.fetchall()
    conn.close()
    return [{"id": c[0], "name": c[1], "phone": c[2], "balance_uzs": c[3], "balance_usd": c[4]} for c in clients]

@app.post("/orders/")
def create_order(order: OrderCreate):
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    cursor.execute('''
        INSERT INTO orders (client_id, service_name, unit_count, total_price, currency, created_at, deadline)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (order.client_id, order.service_name, order.unit_count, order.total_price, order.currency, created_at, order.deadline))
    
    # Valyutaga qarab balans oshirish
    if order.currency == "USD":
        cursor.execute("UPDATE clients SET balance_usd = balance_usd + ? WHERE id = ?", (order.total_price, order.client_id))
    else:
        cursor.execute("UPDATE clients SET balance_uzs = balance_uzs + ? WHERE id = ?", (order.total_price, order.client_id))
        
    conn.commit()
    conn.close()
    return {"message": "Buyurtma saqlandi"}

@app.get("/orders/")
def get_orders():
    conn = sqlite3.connect("milling_center.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT orders.id, clients.name, orders.service_name, orders.unit_count, 
               orders.total_price, orders.currency, orders.created_at, orders.deadline, orders.status
        FROM orders
        JOIN clients ON orders.client_id = clients.id
        ORDER BY orders.id DESC
    ''')
    orders = cursor.fetchall()
    conn.close()
    return orders