import unittest
import json
from app import app, db, Book

class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
        
        self.headers = {'X-API-Key': 'test-api-key'}

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_get_books(self):
        response = self.client.get('/api/books', headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_create_book(self):
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'isbn': '1234567890123',
            'publish_date': '2023-05-01',
            'description': 'A test book description'
        }
        response = self.client.post('/api/books', 
                                    data=json.dumps(book_data),
                                    content_type='application/json',
                                    headers=self.headers)
        self.assertEqual(response.status_code, 201)

    def test_get_nonexistent_book(self):
        response = self.client.get('/api/books/999', headers=self.headers)
        self.assertEqual(response.status_code, 404)

    def test_search_books(self):
        book_data = {
            'title': 'Python Programming',
            'author': 'John Doe',
            'isbn': '1234567890123',
            'publish_date': '2023-05-01',
            'description': 'A book about Python programming'
        }
        self.client.post('/api/books', 
                         data=json.dumps(book_data),
                         content_type='application/json',
                         headers=self.headers)
        
        response = self.client.get('/api/books/search?q=Python', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Python Programming')

if __name__ == '__main__':
    unittest.main()