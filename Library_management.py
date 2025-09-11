import csv
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta

BOOKS_FILE = "books.csv"
STUDENTS_FILE = "students.csv"
LOGS_FILE = "logs.csv"
BASE_PENALTY_RATE = 1
MAX_PENALTY = 50
GRACE_PERIOD = 2

def load_csv(file_name):
    try:
        with open(file_name, mode='r') as file:
            return list(csv.DictReader(file))
    except FileNotFoundError:
        return []

def save_csv(file_name, fieldnames, data):
    with open(file_name, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

class Book:
    def __init__(self, book_id, title, author, available_copies):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.available_copies = int(available_copies)

    def to_csv(self):
        return {
            "book_id": self.book_id,
            "title": self.title,
            "author": self.author,
            "available_copies": self.available_copies
        }

class Student:
    def __init__(self, student_id, name, borrowed_books=None):
        self.student_id = student_id
        self.name = name
        self.borrowed_books = borrowed_books if borrowed_books else []

    def to_csv(self):
        return {
            "student_id": self.student_id,
            "name": self.name,
            "borrowed_books": ",".join(self.borrowed_books)
        }

    def can_borrow(self):
        return len(self.borrowed_books) < 3

class Librarian:
    def __init__(self):
        self.books = [Book(**b) for b in load_csv(BOOKS_FILE)]
        self.students = [
            Student(student_id=s['student_id'], name=s['name'], borrowed_books=s['borrowed_books'].split(','))
            for s in load_csv(STUDENTS_FILE)
        ]
        self.logs = load_csv(LOGS_FILE)

    def search_student(self, query):
        """
        Search for students by name or student ID.
        :param query: The search query string.
        :return: List of matching students as dictionaries.
        """
        return [
            student.to_csv() for student in self.students
            if query.lower() in student.name.lower() or query == student.student_id
        ]


    def search_book(self, query):
        """
        Search for books by title or author.
        :param query: The search query string.
        :return: List of matching books as dictionaries.
        """
        return [
            book.to_csv() for book in self.books
            if query.lower() in book.title.lower() or query.lower() in book.author.lower()
        ]


    def issue_book(self, book_id, student_id):
        book = next((b for b in self.books if b.book_id == book_id), None)
        student = next((s for s in self.students if s.student_id == student_id), None)

        if not book:
            return "Book not found."
        if not student:
            return "Student not found."
        if book.available_copies <= 0:

            return "No copies available."
        if not student.can_borrow():
            return "Student has reached the borrowing limit."

        due_date = datetime.now() + timedelta(days=14)
        book.available_copies -= 1
        student.borrowed_books.append(f"{book_id} (Due: {due_date:%Y-%m-%d})")
        self.update_logs("issue", book_id, student_id)
        self.save_data()
        return f"Book issued successfully. Due date: {due_date:%Y-%m-%d}"


    def return_book(self, book_id, student_id, return_date):
        book = next((b for b in self.books if b.book_id == book_id), None)
        student = next((s for s in self.students if s.student_id == student_id), None)

        if not book or not student:
            return "Book or Student not found."
        
        borrowed = [b for b in student.borrowed_books if book_id in b]
        if not borrowed:
            return "This student did not borrow this book."

        issue_due_date_str = borrowed[0].split("Due: ")[1][:-1]
        penalty = self.calculate_penalty(issue_due_date_str, return_date)

        student.borrowed_books.remove(borrowed[0])
        book.available_copies += 1
        self.update_logs("return", book_id, student_id)
        self.save_data()
        return f"Book returned successfully. Penalty: ${penalty}"

    def calculate_penalty(self, issue_due_date, return_date):
        issue_date = datetime.strptime(issue_due_date, "%Y-%m-%d")
        return_date_obj = datetime.strptime(return_date, "%Y-%m-%d")
        overdue_days = (return_date_obj - issue_date).days - GRACE_PERIOD
        if overdue_days <= 0:
            return 0
        return min(overdue_days * BASE_PENALTY_RATE, MAX_PENALTY)

    def update_logs(self, transaction_type, book_id, student_id):
        self.logs.append({
            "transaction_type": transaction_type,
            "book_id": book_id,
            "student_id": student_id,
            "date": datetime.now().strftime("%Y-%m-%d")
        })
        save_csv(LOGS_FILE, ["transaction_type", "book_id", "student_id", "date"], self.logs)

    def save_data(self):
        save_csv(BOOKS_FILE, ["book_id", "title", "author", "available_copies"], [b.to_csv() for b in self.books])
        save_csv(STUDENTS_FILE, ["student_id", "name", "borrowed_books"], [s.to_csv() for s in self.students])

# GUI and Event Handlers
import tkinter as tk
from tkinter import messagebox, ttk

class LibraryGUI:
    def __init__(self, root):
        self.librarian = Librarian()
        self.root = root
        self.root.title("Library Management System")

        # Notebook for Tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)

        # Book Management Tab
        self.book_frame = tk.Frame(self.notebook)
        self.notebook.add(self.book_frame, text="Books")
        self.setup_book_management()

        # Student Management Tab
        self.student_frame = tk.Frame(self.notebook)
        self.notebook.add(self.student_frame, text="Students")
        self.setup_student_management()

        # Transactions Tab
        self.transaction_frame = tk.Frame(self.notebook)
        self.notebook.add(self.transaction_frame, text="Transactions")
        self.setup_transaction_management()

    def setup_book_management(self):
        # Search Section
        tk.Label(self.book_frame, text="Search Books:").grid(row=0, column=0, pady=5, sticky="w")
        self.book_search_entry = tk.Entry(self.book_frame)
        self.book_search_entry.grid(row=0, column=1, padx=10)
        self.search_book_button = tk.Button(self.book_frame, text="Search", command=self.search_books)
        self.search_book_button.grid(row=0, column=2, padx=10)

        # Display Section
        self.books_display = tk.Text(self.book_frame, height=15, width=70)
        self.books_display.grid(row=1, column=0, columnspan=3, pady=10)

        # Add New Book Section
        tk.Label(self.book_frame, text="Add New Book").grid(row=2, column=0, pady=5, sticky="w")
        self.new_book_id = tk.Entry(self.book_frame)
        self.new_book_title = tk.Entry(self.book_frame)
        self.new_book_author = tk.Entry(self.book_frame)
        self.new_book_copies = tk.Entry(self.book_frame)

        self.new_book_id.grid(row=3, column=1, padx=10)
        self.new_book_title.grid(row=4, column=1, padx=10)
        self.new_book_author.grid(row=5, column=1, padx=10)
        self.new_book_copies.grid(row=6, column=1, padx=10)

        tk.Label(self.book_frame, text="Book ID:").grid(row=3, column=0, sticky="w")
        tk.Label(self.book_frame, text="Title:").grid(row=4, column=0, sticky="w")
        tk.Label(self.book_frame, text="Author:").grid(row=5, column=0, sticky="w")
        tk.Label(self.book_frame, text="Copies:").grid(row=6, column=0, sticky="w")

        self.add_book_button = tk.Button(self.book_frame, text="Add Book", command=self.add_book)
        self.add_book_button.grid(row=7, column=0, columnspan=2, pady=10)

    def setup_student_management(self):
        # Search Section
        tk.Label(self.student_frame, text="Search Students:").grid(row=0, column=0, pady=5, sticky="w")
        self.student_search_entry = tk.Entry(self.student_frame)
        self.student_search_entry.grid(row=0, column=1, padx=10)
        self.search_student_button = tk.Button(self.student_frame, text="Search", command=self.search_students)
        self.search_student_button.grid(row=0, column=2, padx=10)

        # Display Section
        self.students_display = tk.Text(self.student_frame, height=15, width=70)
        self.students_display.grid(row=1, column=0, columnspan=3, pady=10)

        # Add New Student Section
        tk.Label(self.student_frame, text="Add New Student").grid(row=2, column=0, pady=5, sticky="w")
        self.new_student_id = tk.Entry(self.student_frame)
        self.new_student_name = tk.Entry(self.student_frame)

        self.new_student_id.grid(row=3, column=1, padx=10)
        self.new_student_name.grid(row=4, column=1, padx=10)

        tk.Label(self.student_frame, text="Student ID:").grid(row=3, column=0, sticky="w")
        tk.Label(self.student_frame, text="Name:").grid(row=4, column=0, sticky="w")

        self.add_student_button = tk.Button(self.student_frame, text="Add Student", command=self.add_student)
        self.add_student_button.grid(row=5, column=0, columnspan=2, pady=10)

    def setup_transaction_management(self):
        # Issue Book Section
        tk.Label(self.transaction_frame, text="Book ID:").grid(row=0, column=0, sticky="w")
        self.book_id_entry = tk.Entry(self.transaction_frame)
        self.book_id_entry.grid(row=0, column=1, padx=10)

        tk.Label(self.transaction_frame, text="Student ID:").grid(row=1, column=0, sticky="w")
        self.student_id_entry = tk.Entry(self.transaction_frame)
        self.student_id_entry.grid(row=1, column=1, padx=10)

        self.issue_button = tk.Button(self.transaction_frame, text="Issue Book", command=self.issue_book)
        self.issue_button.grid(row=2, column=0, padx=10, pady=10)

        # Return Book Section
        tk.Label(self.transaction_frame, text="Return Date (YYYY-MM-DD):").grid(row=3, column=0, sticky="w")
        self.return_date_entry = tk.Entry(self.transaction_frame)
        self.return_date_entry.grid(row=3, column=1, padx=10)

        self.return_button = tk.Button(self.transaction_frame, text="Return Book", command=self.return_book)
        self.return_button.grid(row=4, column=0, padx=10, pady=10)

        self.due_date_display = tk.Label(self.transaction_frame, text="", font=("Arial", 12))
        self.due_date_display.grid(row=5, column=0, columnspan=2, pady=10)

        self.penalty_display = tk.Label(self.transaction_frame, text="Penalty: $0", font=("Arial", 12))
        self.penalty_display.grid(row=6, column=0, columnspan=2, pady=10)

    def search_books(self):
        query = self.book_search_entry.get()
        results = self.librarian.search_book(query)
        self.books_display.delete("1.0", tk.END)
        if not results:
            self.books_display.insert(tk.END, "No books found.")
        else:
            for book in results:
                self.books_display.insert(tk.END, f"ID: {book['book_id']}, Title: {book['title']}, Author: {book['author']}, Available: {book['available_copies']}\n")

    def search_students(self):
        query = self.student_search_entry.get()
        results = self.librarian.search_student(query)
        self.students_display.delete("1.0", tk.END)
        if not results:
            self.students_display.insert(tk.END, "No students found.")
        else:
            for student in results:
                self.students_display.insert(tk.END, f"ID: {student['student_id']}, Name: {student['name']}, Borrowed: {student['borrowed_books']}\n")

    def add_book(self):
        book_id = self.new_book_id.get()
        title = self.new_book_title.get()
        author = self.new_book_author.get()
        copies = self.new_book_copies.get()

        if not (book_id and title and author and copies.isdigit()):
            messagebox.showerror("Error", "Please fill in all fields correctly.")
            return

        new_book = Book(book_id, title, author, int(copies))
        self.librarian.books.append(new_book)
        self.librarian.save_data()
        messagebox.showinfo("Success", "Book added successfully.")
        self.search_books()

    def add_student(self):
        student_id = self.new_student_id.get()
        name = self.new_student_name.get()

        if not (student_id and name):
            messagebox.showerror("Error", "Please fill in all fields correctly.")
            return

        new_student = Student(student_id, name)
        self.librarian.students.append(new_student)
        self.librarian.save_data()
        messagebox.showinfo("Success", "Student added successfully.")
        self.search_students()

    def issue_book(self):
        book_id = self.book_id_entry.get()
        student_id = self.student_id_entry.get()

        result = self.librarian.issue_book(book_id, student_id)
        if "Due date" in result:
            due_date = result.split("Due date: ")[-1]
            self.due_date_display.config(text=f"Due Date: {due_date}")
        else:
            self.due_date_display.config(text="")

        messagebox.showinfo("Info", result)
        self.search_books()

    def return_book(self):
        book_id = self.book_id_entry.get()
        student_id = self.student_id_entry.get()
        return_date = self.return_date_entry.get()

        try:
            datetime.strptime(return_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
            return

        result = self.librarian.return_book(book_id, student_id, return_date)
        if "Penalty" in result:
            penalty = result.split("Penalty: $")[-1]
            self.penalty_display.config(text=f"Penalty: ${penalty}")
        else:
            self.penalty_display.config(text="Penalty: $0")

        messagebox.showinfo("Info", result)
        self.search_books()
        self.search_students()

if __name__ == "__main__":
    root = tk.Tk()
    app = LibraryGUI(root)
    root.geometry("800x900")
    root.mainloop()