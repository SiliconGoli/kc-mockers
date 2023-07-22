from flask import Flask, jsonify, make_response, render_template
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io
import sqlite3
import asyncio
import aiohttp
import PIL
from PIL import Image
from flask_cors import CORS
app = Flask(__name__)
CORS(app)


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
    return render_template('index.html')

@app.route('/questions/<int:no_of_questions>', methods=['GET'])
def generate_questions(no_of_questions):
    if no_of_questions < 1:
        return jsonify({"message": "Invalid number of questions requested. Must be a positive integer."}), 400

    query = "SELECT image FROM questions ORDER BY RANDOM() LIMIT ?;"
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
        query = "SELECT image FROM questions WHERE topic=? ORDER BY RANDOM() LIMIT ?;"
        topic_questions = fetch_questions_from_db(query, topic, no_of_questions)
        selected_questions.extend(topic_questions)

    conn.close()
    return jsonify({"questions": [question[0] for question in selected_questions]}), 200

'''TODO : Fix this route by removing connection to local database and connecting to the remote database'''

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

async def fetch_image(session, image_url):
    async with session.get(image_url) as response:
        return await response.read()

async def generate_pdf_async(no_of_questions):
    url = f"https://kc-mockers.onrender.com/questions/{no_of_questions}"
    async with aiohttp.ClientSession() as session:
        response = await session.get(url)
        image_urls = await response.json()

        if not image_urls['questions']:
            return "No image questions found.", 404

        pdf_buffer = io.BytesIO()
        pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=letter)

        # New layout settings
        images_per_row = 1
        margin_x = 50
        margin_y = 50
        fixed_width = (letter[0] - 2 * margin_x) / images_per_row
        divider_height = 5

        def draw_image(image_data, x, y, width, height):
            try:
                img = Image.open(io.BytesIO(image_data))
                pdf_canvas.drawImage(ImageReader(img), x, y, width=width, height=height)
            except PIL.UnidentifiedImageError:
                print(f"UnidentifiedImageError: Cannot identify image data: {image_data}")
            except Exception as e:
                print(f"Failed to open image from URL: {image_url}. Error: {e}")

        current_y = letter[1] - margin_y
        current_x = margin_x

        tasks = []
        for index, image_url in enumerate(image_urls['questions']):
            tasks.append(fetch_image(session, image_url))

            if len(tasks) == images_per_row:
                images_data = await asyncio.gather(*tasks)
                for image_data in images_data:
                    try:
                        img = Image.open(io.BytesIO(image_data))
                        adjusted_height = (fixed_width / img.width) * img.height
                        draw_image(image_data, current_x, current_y - adjusted_height, fixed_width, adjusted_height)
                        current_x += fixed_width
                    except PIL.UnidentifiedImageError:
                        print(f"UnidentifiedImageError: Cannot identify image data: {image_data}")
                    except Exception as e:
                        print(f"Failed to process image from URL: {image_url}. Error: {e}")

                tasks = []

            if index % images_per_row == images_per_row - 1:
                current_x = margin_x
                current_y -= adjusted_height + divider_height

                # Draw horizontal divider line between rows
                if index < len(image_urls['questions']) - 1:
                    pdf_canvas.setStrokeColorRGB(0, 0, 0)  # Black color for the divider
                    pdf_canvas.setLineWidth(0.5)
                    pdf_canvas.line(margin_x, current_y, letter[0] - margin_x, current_y)

            # Start a new page if the current page is full
            if current_y < margin_y:
                pdf_canvas.showPage()
                current_y = letter[1] - margin_y
                current_x = margin_x

        # Fetch the remaining images if not enough to complete a row
        if tasks:
            images_data = await asyncio.gather(*tasks)
            for image_data in images_data:
                adjusted_height = (fixed_width / Image.open(io.BytesIO(image_data)).width) * Image.open(io.BytesIO(image_data)).height
                draw_image(image_data, current_x, current_y - adjusted_height, fixed_width, adjusted_height)
                current_x += fixed_width

        pdf_canvas.save()
        pdf_buffer.seek(0)

        # Set the response headers for the PDF file download
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=questions.pdf'
        return response

# Your Flask route can now call the asynchronous function
@app.route('/generate-pdf/<int:no_of_questions>', methods=['GET'])
def generate_pdf_route(no_of_questions):
    return asyncio.run(generate_pdf_async(no_of_questions))


if __name__ == '__main__':
    app.run(debug=True)
