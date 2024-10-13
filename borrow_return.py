from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO
import time
from utils import connect_db

# Inisialisasi RFID Reader
reader = SimpleMFRC522()

def read_rfid_card():
    """Membaca RFID card dan mengembalikan UID."""
    try:
        print("Please scan your RFID card...")
        rfid_code = reader.read()[0]  # Baca UID kartu siswa
        return rfid_code
    except Exception as e:
        print(f"Error reading RFID: {e}")
        return None
    finally:
        GPIO.cleanup()

def wait_until_card_removed():
    """Menunggu sampai kartu RFID dilepas."""
    print("Please remove your RFID card...")
    while True:
        try:
            id, _ = reader.read_no_block()  # Membaca tanpa blokir
            if id is None:
                print("Card removed.")
                break  # Keluar dari loop jika kartu tidak terbaca
            time.sleep(0.5)  # Tunggu sebentar sebelum membaca lagi
        except Exception as e:
            print(f"Error while waiting for card removal: {e}")
            break

def process_borrow_return(student_id):
    """Proses peminjaman atau pengembalian buku."""
    try:
        print("Please scan the book's RFID tag...")
        rfid_code = reader.read()[0]  # Membaca UID buku

        conn = connect_db()
        cursor = conn.cursor()

        # Cek status buku di database berdasarkan RFID tag
        cursor.execute("SELECT id, title, status FROM books WHERE rfid_code = ?", (rfid_code,))
        book = cursor.fetchone()

        if book:
            book_id, title, status = book

            if status == 'tersedia':
                # Proses peminjaman buku
                borrow_date = time.strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('''
                    INSERT INTO borrowed_books (student_id, book_id, borrow_date)
                    VALUES (?, ?, ?)
                ''', (student_id, book_id, borrow_date))
                cursor.execute("UPDATE books SET status = 'dipinjam' WHERE id = ?", (book_id,))
                conn.commit()
                print(f"Book '{title}' borrowed successfully.")
            elif status == 'dipinjam':
                # Proses pengembalian buku
                return_date = time.strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('''
                    UPDATE borrowed_books SET return_date = ?
                    WHERE book_id = ? AND student_id = ? AND return_date IS NULL
                ''', (return_date, book_id, student_id))
                cursor.execute("UPDATE books SET status = 'tersedia' WHERE id = ?", (book_id,))
                conn.commit()
                print(f"Book '{title}' returned successfully.")
            else:
                print(f"Error: Unknown book status '{status}'.")
        else:
            print("Error: Book not found.")

        conn.close()

    finally:
        GPIO.cleanup()

def borrow_return():
    """Fungsi utama untuk proses peminjaman/pengembalian buku."""
    # Baca kartu RFID siswa
    student_rfid = read_rfid_card()
    
    if student_rfid is None:
        print("Error: No card detected.")
        return

    # Verifikasi apakah siswa terdaftar di database
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM students WHERE rfid_code = ?", (student_rfid,))
    student = cursor.fetchone()
    conn.close()

    if student:
        student_id, student_name = student
        print(f"Authenticated student: {student_name}")

        # Tunggu hingga kartu siswa dilepas
        wait_until_card_removed()

        # Minta siswa untuk scan buku
        process_borrow_return(student_id)
    else:
        print("Error: Student not found.")

if __name__ == '__main__':
    borrow_return()
