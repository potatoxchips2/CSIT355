import sqlite3


DB_NAME = "finalProject.db"


def connect_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables(conn):
    existing_student_columns = [
        row[1] for row in conn.execute("PRAGMA table_info(Student)").fetchall()
    ]
    existing_course_columns = [
        row[1] for row in conn.execute("PRAGMA table_info(Course)").fetchall()
    ]

    reset_student = (
        existing_student_columns
        and existing_student_columns != ["student_id", "student_name"]
    )
    reset_course = existing_course_columns and existing_course_columns != [
        "course_id",
        "course_name",
        "credits",
    ]

    if reset_student or reset_course:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DROP TABLE IF EXISTS Enrolled")
        conn.execute("DROP TABLE IF EXISTS Course")
        conn.execute("DROP TABLE IF EXISTS Student")
        conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS Student (
            student_id INTEGER PRIMARY KEY,
            student_name TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS Course (
            course_id TEXT PRIMARY KEY,
            course_name TEXT NOT NULL,
            credits INTEGER NOT NULL CHECK (credits > 0)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS Enrolled (
            student_id INTEGER NOT NULL,
            course_id TEXT NOT NULL,
            PRIMARY KEY (student_id, course_id),
            FOREIGN KEY (student_id) REFERENCES Student(student_id)
                ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES Course(course_id)
                ON DELETE CASCADE
        )
        """
    )
    conn.commit()


def seed_data(conn):
    student_count = conn.execute("SELECT COUNT(*) FROM Student").fetchone()[0]
    course_count = conn.execute("SELECT COUNT(*) FROM Course").fetchone()[0]
    enrollment_count = conn.execute("SELECT COUNT(*) FROM Enrolled").fetchone()[0]

    if student_count > 0 or course_count > 0 or enrollment_count > 0:
        return

    students = [
        (1001, "Aria Montgomery"),
        (1002, "Spencer Hastings"),
        (1003, "Hanna Marin"),
        (1004, "Emily Fields"),
        (1005, "Alison DiLaurentis"),
    ]

    courses = [
        ("CSIT101", "Introduction to Programming", 3),
        ("CSIT210", "Database Systems", 3),
        ("CSIT255", "Web Development", 3),
        ("CSIT320", "Network Security", 4),
        ("CSIT355", "Systems Analysis and Design", 3),
    ]

    enrollments = [
        (1001, "CSIT101"),
        (1001, "CSIT210"),
        (1002, "CSIT101"),
        (1002, "CSIT255"),
        (1003, "CSIT320"),
        (1003, "CSIT355"),
        (1004, "CSIT210"),
        (1004, "CSIT355"),
        (1005, "CSIT255"),
        (1005, "CSIT320"),
    ]

    conn.executemany(
        """
        INSERT INTO Student
            (student_id, student_name)
        VALUES (?, ?)
        """,
        students,
    )
    conn.executemany(
        """
        INSERT INTO Course
            (course_id, course_name, credits)
        VALUES (?, ?, ?)
        """,
        courses,
    )
    conn.executemany(
        """
        INSERT INTO Enrolled
            (student_id, course_id)
        VALUES (?, ?)
        """,
        enrollments,
    )
    conn.commit()


def get_required_text(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("This field cannot be blank.")


def get_student(conn, student_id):
    return conn.execute(
        """
        SELECT student_id, student_name
        FROM Student
        WHERE student_id = ?
        """,
        (student_id,),
    ).fetchone()


def create_student(conn):
    print("\nCreate New Student")
    while True:
        student_id_text = input("Student ID: ").strip()
        if not student_id_text.isdigit():
            print("Student ID must be a positive number.")
            continue

        student_id = int(student_id_text)
        if get_student(conn, student_id):
            print("That student ID already exists. Please enter another ID.")
            continue
        break

    student_name = get_required_text("Student name: ")
    conn.execute(
        """
        INSERT INTO Student (student_id, student_name)
        VALUES (?, ?)
        """,
        (student_id, student_name),
    )
    conn.commit()
    print(f"Student {student_name} was created.")
    return get_student(conn, student_id)


def select_active_student(conn):
    while True:
        user_input = input("Enter student ID, or -1 to create a new student: ").strip()
        if user_input == "-1":
            return create_student(conn)

        if not user_input.isdigit():
            print("Please enter a valid student ID.")
            continue

        student = get_student(conn, int(user_input))
        if student:
            return student

        print("Student was not found. Try again, or enter -1 to create a student.")


def print_course_rows(rows):
    if not rows:
        print("No courses found.")
        return

    print("\nCourse ID   Course Name                         Credits")
    print("-" * 56)
    for course_id, course_name, credits in rows:
        print(f"{course_id:<10}  {course_name:<34}  {credits}")


def list_courses(conn):
    rows = conn.execute(
        """
        SELECT course_id, course_name, credits
        FROM Course
        ORDER BY course_id
        """
    ).fetchall()
    print_course_rows(rows)


def enroll_student(conn, student):
    course_id = get_required_text("Enter course ID to enroll in: ").upper()
    course = conn.execute(
        "SELECT course_id FROM Course WHERE upper(course_id) = ?",
        (course_id,),
    ).fetchone()

    if not course:
        print("That course does not exist.")
        return

    existing = conn.execute(
        """
        SELECT 1
        FROM Enrolled
        WHERE student_id = ? AND course_id = ?
        """,
        (student[0], course[0]),
    ).fetchone()
    if existing:
        print("You are already enrolled in that course.")
        return

    conn.execute(
        "INSERT INTO Enrolled (student_id, course_id) VALUES (?, ?)",
        (student[0], course[0]),
    )
    conn.commit()
    print("Enrollment completed.")


def withdraw_student(conn, student):
    course_id = get_required_text("Enter course ID to withdraw from: ").upper()
    cursor = conn.execute(
        """
        DELETE FROM Enrolled
        WHERE student_id = ?
          AND course_id = (
              SELECT course_id
              FROM Course
              WHERE upper(course_id) = ?
          )
        """,
        (student[0], course_id),
    )
    conn.commit()

    if cursor.rowcount == 0:
        print("No enrollment was found for that course.")
    else:
        print("Withdrawal completed.")


def search_courses(conn):
    search_text = get_required_text("Enter part of the course name: ")
    rows = conn.execute(
        """
        SELECT course_id, course_name, credits
        FROM Course
        WHERE lower(course_name) LIKE lower(?)
        ORDER BY course_id
        """,
        (f"%{search_text}%",),
    ).fetchall()
    print_course_rows(rows)


def list_my_classes(conn, student):
    rows = conn.execute(
        """
        SELECT c.course_id, c.course_name, c.credits
        FROM Enrolled e
        JOIN Course c ON e.course_id = c.course_id
        WHERE e.student_id = ?
        ORDER BY c.course_id
        """,
        (student[0],),
    ).fetchall()
    print_course_rows(rows)


def show_menu(student):
    student_id, student_name = student
    print(f"\nActive student: {student_id} - {student_name}")
    print("L - List all courses")
    print("E - Enroll in a course")
    print("W - Withdraw from a course")
    print("S - Search courses by name")
    print("M - My Classes")
    print("X - Exit")


def run_menu(conn, student):
    while True:
        show_menu(student)
        choice = input("Select an option: ").strip().upper()

        if choice == "L":
            list_courses(conn)
        elif choice == "E":
            enroll_student(conn, student)
        elif choice == "W":
            withdraw_student(conn, student)
        elif choice == "S":
            search_courses(conn)
        elif choice == "M":
            list_my_classes(conn, student)
        elif choice == "X":
            print("Goodbye.")
            break
        else:
            print("Invalid option. Please select L, E, W, S, M, or X.")


def main():
    with connect_db() as conn:
        create_tables(conn)
        seed_data(conn)
        active_student = select_active_student(conn)
        run_menu(conn, active_student)


if __name__ == "__main__":
    main()
