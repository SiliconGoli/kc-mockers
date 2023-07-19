import requests
from faker import Faker
import random
import datetime

def insert_question(data):
    url = 'http://127.0.0.1:5000/questions'
    response = requests.post(url, json=data)

    if response.status_code == 201:
        print("Data inserted successfully.")
    else:
        print("Failed to insert data:", response.json())

if __name__ == '__main__':
    # Sample data for inserting into the database
    fake = Faker()

    data_list = []

    for _ in range(20):
        data = {
            "subject": fake.word(ext_word_list=["Science", "Mathematics", "History", "English", "Geography"]),
            "topic": fake.word(),
            "subtopic": fake.word(),
            "question": fake.sentence(),
            "answer": fake.paragraph(),
            "image": fake.image_url(),
            "difficulty": random.choice(["Easy", "Medium", "Hard"]),
            "status": random.choice(["Active", "Inactive"]),
            "created_at": fake.date_this_decade().strftime('%Y-%m-%d'),
            "updated_at": fake.date_this_decade().strftime('%Y-%m-%d')
        }
        data_list.append(data)


    # Insert data into the database by making POST requests to the /questions endpoint
    for i in range(len(data_list)):
        insert_question(data_list[i])
