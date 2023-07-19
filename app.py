from flask import Flask, jsonify, request, Response
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import sqlite3

app = Flask(__name__)

def create_database():
    conn = sqlite3.connect('questions.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT,
                    topic TEXT,
                    subtopic TEXT,
                    question TEXT,
                    answer TEXT,
                    image TEXT,
                    pdf TEXT,
                    video TEXT,
                    link TEXT,
                    tags TEXT,
                    difficulty TEXT,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )''')

    conn.commit()
    conn.close()

# Helper function to fetch questions from the SQLite database
def fetch_questions_from_db(query, *args):
    conn = sqlite3.connect('questions.db')
    c = conn.cursor()
    c.execute(query, args)
    questions = c.fetchall()
    conn.close()
    return questions
@app.route('/')
def index():
    return("Hello")

@app.route('/questions', methods=['POST'])
def insert_questions():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No data provided in the request body."}), 400

    conn = sqlite3.connect('questions.db')
    c = conn.cursor()

    try:
        # Insert the data into the database
        c.execute('''INSERT INTO questions 
                    (subject, topic, subtopic, question, answer, image, pdf, video, link, tags, difficulty, status, created_at, updated_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);''',
                  (data.get('subject', ''),
                   data.get('topic', ''),
                   data.get('subtopic', ''),
                   data.get('question', ''),
                   data.get('answer', ''),
                   data.get('image', ''),
                   data.get('pdf', ''),
                   data.get('video', ''),
                   data.get('link', ''),
                   data.get('tags', ''),
                   data.get('difficulty', ''),
                   data.get('status', ''),
                   data.get('created_at', ''),
                   data.get('updated_at', '')))

        conn.commit()
        conn.close()
        return jsonify({"message": "Data inserted successfully."}), 201

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"message": "Error occurred while inserting data.", "error": str(e)}), 500

@app.route('/questions/<int:no_of_questions>', methods=['GET'])
def generate_questions(no_of_questions):
    if no_of_questions < 1:
        return jsonify({"message": "Invalid number of questions requested. Must be a positive integer."}), 400

    query = "SELECT question FROM questions ORDER BY RANDOM() LIMIT ?;"
    questions = fetch_questions_from_db(query, no_of_questions)

    return jsonify({"questions": [question[0] for question in questions]}), 200


@app.route('/questions/topic/<string:topics>/<int:no_of_questions>', methods=['GET'])
def generate_questions_by_topics(topics, no_of_questions):
    topic_list = topics.split(',')

    valid_topics = []
    for topic in topic_list:
        valid_topics.append(topic)

    if not valid_topics:
        return jsonify({"message": "No valid topics found."}), 404

    if no_of_questions < 1:
        return jsonify({"message": "Invalid number of questions requested. Must be a positive integer."}), 400

    conn = sqlite3.connect('questions.db')
    c = conn.cursor()

    selected_questions = []
    for topic in valid_topics:
        query = "SELECT question FROM questions WHERE topic=? ORDER BY RANDOM() LIMIT ?;"
        topic_questions = fetch_questions_from_db(query, topic, no_of_questions)
        selected_questions.extend(topic_questions)

    conn.close()
    return jsonify({"questions": [question[0] for question in selected_questions]}), 200

@app.route('/questions/year/<int:year>/<int:no_of_questions>', methods=['GET'])
def generate_questions_by_year(year, no_of_questions):
    if no_of_questions < 1:
        return jsonify({"message": "Invalid number of questions requested. Must be a positive integer."}), 400

    conn = sqlite3.connect('questions.db')
    c = conn.cursor()

    query = "SELECT question FROM questions WHERE CAST(strftime('%Y', created_at) AS INTEGER) = ? ORDER BY RANDOM() LIMIT ?;"
    year_questions = fetch_questions_from_db(query, year, no_of_questions)

    conn.close()
    return jsonify({"questions": [question[0] for question in year_questions]}), 200

@app.route('/generate-pdf', methods=['GET'])
def generate_pdf():
    topics = request.args.get('topics', 'general')
    year = int(request.args.get('year', 0))
    no_of_questions = int(request.args.get('no_of_questions', 5))

    conn = sqlite3.connect('questions.db')
    c = conn.cursor()

    query = "SELECT question FROM questions WHERE topic IN ({}) AND CAST(strftime('%Y', created_at) AS INTEGER) = ? ORDER BY RANDOM() LIMIT ?;"
    topic_list = topics.split(',')
    placeholders = ','.join(['?' for _ in range(len(topic_list))])
    query = query.format(placeholders)

    # Append year to the topic_list so that we can use it as the parameter for the query
    topic_list.append(year)
    topic_list.append(no_of_questions)

    questions = fetch_questions_from_db(query, *topic_list)

    conn.close()

    if not questions:
        return jsonify({"message": "No questions provided."}), 400

    # Generate PDF
    pdf_buffer = create_pdf(questions)

    # Set the appropriate response headers
    headers = {
        'Content-Disposition': 'inline; filename=questions.pdf',
        'Content-Type': 'application/pdf'
    }

    return Response(pdf_buffer, headers=headers)

def create_pdf(questions):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    # Write the questions to the PDF
    y = 750
    for question in questions:
        pdf.drawString(100, y, question[0])
        y -= 50

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer.getvalue()

if __name__ == '__main__':
    create_database()
    app.run(debug=True)
