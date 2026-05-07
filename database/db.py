import psycopg2
from core.config import DATABASE_URL
from core.logger import logger


def get_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Ma'lumotlar bazasiga ulanishda xato: {e}")
        return None


def safe_close(conn):
    if conn is not None:
        conn.close()


def init_db():
    conn = get_connection()
    if not conn:
        return
    try:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id SERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                "desc" TEXT NULL,
                photo_path TEXT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                description TEXT,
                phone_number TEXT,
                activity BOOLEAN DEFAULT TRUE
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS order_offer (
                id SERIAL PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                message TEXT,
                order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                driver_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                notif_id INTEGER NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,  
                from_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                message TEXT,
                order_id INTEGER,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"DB Init xatosi: {e}")
    finally:
        safe_close(conn)


def create_user(full_name, phone, password, role):
    conn = get_connection()
    if not conn:
        return False
    try:
        c = conn.cursor()
        c.execute("INSERT INTO users (full_name, phone, password, role) VALUES (%s,%s,%s,%s) RETURNING id",
                  (full_name, phone, password, role))
        user_id = c.fetchone()[0]
        conn.commit()
        return user_id
    except Exception as e:
        logger.error(f"User yaratishda xato: {e}")
        return False
    finally:
        safe_close(conn)


def delete_user(user_id):
    conn = get_connection()
    if not conn:
        return
    try:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    finally:
        safe_close(conn)


def get_user_by_phone(phone):
    conn = get_connection()
    if not conn:
        return []
    try:
        c = conn.cursor()
        c.execute("SELECT id, full_name, phone, role, \"desc\", photo_path FROM users WHERE phone=%s", (phone,))
        return c.fetchall()
    finally:
        safe_close(conn)


def get_user_by_id(user_id):
    conn = get_connection()
    if not conn:
        return []
    try:
        c = conn.cursor()
        c.execute("SELECT phone FROM users WHERE id=%s", (user_id,))
        return c.fetchall()
    finally:
        safe_close(conn)


def update_pr(photo, desc, full_name, user_ids):
    conn = get_connection()
    if not conn:
        return False
    try:
        c = conn.cursor()
        c.execute("UPDATE users SET full_name=%s, photo_path=%s, \"desc\"=%s WHERE id=%s",
                  (full_name, photo, desc, user_ids))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Profil yangilashda xato: {e}")
        return False
    finally:
        safe_close(conn)


def checker_user(phone, psw):
    conn = get_connection()
    if not conn:
        return False
    try:
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE phone=%s", (phone,))
        res = c.fetchone()
        return res[0] == psw if res else False
    finally:
        safe_close(conn)


def create_order(description, phone):
    conn = get_connection()
    if not conn:
        return
    try:
        c = conn.cursor()
        c.execute("INSERT INTO orders (description, phone_number, activity) VALUES (%s, %s, %s)",
                  (description, phone, True))
        conn.commit()
    finally:
        safe_close(conn)


def get_offers_by_order(order_id):
    conn = get_connection()
    if not conn:
        return []
    try:
        c = conn.cursor()
        c.execute("""
            SELECT oo.id, oo.status, oo.message, u.full_name, u.photo_path, oo.driver_id
            FROM order_offer oo
            JOIN users u ON oo.driver_id = u.id
            WHERE oo.order_id = %s
        """, (order_id,))
        return c.fetchall()
    finally:
        safe_close(conn)


def get_all_orders():
    conn = get_connection()
    if not conn:
        return []
    try:
        c = conn.cursor()
        c.execute("SELECT phone_number, description, activity, id FROM orders")
        return c.fetchall()
    finally:
        safe_close(conn)


def get_order_by_id(order_id):
    conn = get_connection()
    if not conn:
        return None
    try:
        c = conn.cursor()
        c.execute("SELECT description, activity, id, phone_number FROM orders WHERE id=%s", (order_id,))
        return c.fetchone()
    finally:
        safe_close(conn)


def inactivate_order(order_id, manager_phone):
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM orders WHERE id = %s AND phone_number = %s", (order_id, manager_phone))
        order = c.fetchone()
        if not order:
            logger.warning(
                f"Validatsiya xatosi: Manager {manager_phone} o'ziga tegishli bo'lmagan #{order_id} orderni o'chirmoqchi.")
            a = "USER NOT"
            return a
        c.execute("UPDATE orders SET activity = FALSE WHERE id = %s", (order_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"O'chirishda backend xatosi: {e}")
        return False
    finally:
        safe_close(conn)


def get_orders_by_owner(phone):
    conn = get_connection()
    if not conn:
        return []
    try:
        c = conn.cursor()
        c.execute("SELECT description, activity, id FROM orders WHERE phone_number=%s", (phone,))
        return c.fetchall()
    finally:
        safe_close(conn)


def create_order_offer(order_id, message, driver_id):
    conn = get_connection()
    if not conn:
        return
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO order_offer (status, message, order_id, driver_id)
            VALUES (%s, %s, %s, %s)
        """, ("pending", str(message), order_id, driver_id))
        conn.commit()
    finally:
        safe_close(conn)


def get_driver_offers(user_id):
    conn = get_connection()
    if not conn:
        return []
    try:
        c = conn.cursor()
        c.execute("SELECT id, status, message, order_id FROM order_offer WHERE driver_id = %s", (user_id,))
        return c.fetchall()
    finally:
        safe_close(conn)


def approve_driver_offer(offer_id, driver_id, order_id, manager_id):
    conn = get_connection()
    if not conn:
        return False
    try:
        c = conn.cursor()
        c.execute("UPDATE order_offer SET status = 'accepted' WHERE id = %s", (offer_id,))
        msg = f"Sizning #{order_id}-sonli buyurtma uchun taklifingiz qabul qilindi."
        c.execute("INSERT INTO notifications (user_id, from_id, message, order_id) VALUES (%s, %s, %s, %s)",
                  (driver_id, manager_id, msg, order_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Taklifni qabul qilishda xato: {e}")
        return False
    finally:
        safe_close(conn)


def reject_driver_offer(offer_id):
    conn = get_connection()
    if not conn:
        return False
    try:
        c = conn.cursor()
        c.execute("UPDATE order_offer SET status = 'rejected' WHERE id = %s", (offer_id,))
        conn.commit()
        return True
    finally:
        safe_close(conn)


def create_notification(user_id, message, order_id, from_id):
    conn = get_connection()
    if not conn:
        return
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO notifications (user_id, message, order_id, is_read, from_id) 
            VALUES (%s, %s, %s, FALSE, %s) RETURNING id
        """, (user_id, message, order_id, from_id))
        notif_id = c.fetchone()[0]
        c.execute("UPDATE order_offer SET notif_id = %s WHERE order_id = %s AND driver_id = %s",
                  (notif_id, order_id, from_id))
        conn.commit()
    finally:
        safe_close(conn)


def get_unread_notifications(user_id):
    conn = get_connection()
    if not conn:
        return []
    try:
        c = conn.cursor()
        c.execute("""
            SELECT id, message, order_id, created_at 
            FROM notifications 
            WHERE user_id = %s AND is_read = FALSE 
            ORDER BY created_at DESC
        """, (user_id,))
        return c.fetchall()
    finally:
        safe_close(conn)


def mark_as_read(notif_id):
    conn = get_connection()
    if not conn:
        return
    try:
        c = conn.cursor()
        c.execute("UPDATE notifications SET is_read = TRUE WHERE id = %s", (notif_id,))
        conn.commit()
    finally:
        safe_close(conn)


def get_full_notification_data(notif_id):
    conn = get_connection()
    if not conn:
        return None
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM notifications WHERE id = %s", (notif_id,))
        notif = c.fetchone()
        if not notif:
            return None
        c.execute("SELECT id, description, phone_number, activity FROM orders WHERE id = %s", (notif[4],))
        order = c.fetchone()
        c.execute("SELECT id, full_name, phone, role, \"desc\", photo_path FROM users WHERE id = %s", (notif[2],))
        driver = c.fetchone()
        c.execute("SELECT id, status, message FROM order_offer WHERE notif_id = %s", (notif_id,))
        offer = c.fetchone()
        return {"notif": notif, "order": order, "driver": driver, "offer": offer}
    finally:
        safe_close(conn)
