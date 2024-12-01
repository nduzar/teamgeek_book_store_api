import os
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, validate, ValidationError
from werkzeug.exceptions import NotFound, BadRequest
from flask_cors import CORS
import boto3

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///library.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# API key for basic authentication
API_KEY = os.environ.get('API_KEY', 'your-api-key-here')

# AWS S3 configuration
S3_BUCKET = os.environ.get('S3_BUCKET', 'your-s3-bucket-name')
s3_client = boto3.client('s3')

# Authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == API_KEY:
            return f(*args, **kwargs)
        return jsonify({"error": "Invalid API key"}), 401
    return decorated

# Book Model
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(13), unique=True, nullable=False)
    publish_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    cover_image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Book Schema for validation and serialization
class BookSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    author = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    isbn = fields.Str(required=True, validate=validate.Length(equal=13))
    publish_date = fields.Date(required=True)
    description = fields.Str()
    cover_image_url = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

book_schema = BookSchema()
books_schema = BookSchema(many=True)

@app.route('/api/books', methods=['GET'])
@require_api_key
def get_books():
    books = Book.query.all()
    return jsonify(books_schema.dump(books)), 200

@app.route('/api/books/<int:id>', methods=['GET'])
@require_api_key
def get_book(id):
    book = Book.query.get_or_404(id)
    return jsonify(book_schema.dump(book)), 200

@app.route('/api/books', methods=['POST'])
@require_api_key
def create_book():
    try:
        data = book_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    new_book = Book(**data)
    db.session.add(new_book)
    db.session.commit()
    return jsonify(book_schema.dump(new_book)), 201

@app.route('/api/books/<int:id>', methods=['PUT'])
@require_api_key
def update_book(id):
    book = Book.query.get_or_404(id)
    
    try:
        data = book_schema.load(request.json, partial=True)
    except ValidationError as err:
        return jsonify(err.messages), 400

    for key, value in data.items():
        setattr(book, key, value)

    db.session.commit()
    return jsonify(book_schema.dump(book)), 200

@app.route('/api/books/<int:id>', methods=['DELETE'])
@require_api_key
def delete_book(id):
    book = Book.query.get_or_404(id)
    db.session.delete(book)
    db.session.commit()
    return '', 204

@app.route('/api/books/<int:id>/cover', methods=['POST'])
@require_api_key
def upload_cover(id):
    book = Book.query.get_or_404(id)
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = f"{book.isbn}_cover.jpg"
        s3_client.upload_fileobj(file, S3_BUCKET, filename)
        book.cover_image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{filename}"
        db.session.commit()
        return jsonify({"message": "Cover image uploaded successfully", "url": book.cover_image_url}), 200

@app.route('/api/books/search', methods=['GET'])
@require_api_key
def search_books():
    query = request.args.get('q', '')
    books = Book.query.filter(
        (Book.title.ilike(f'%{query}%')) |
        (Book.author.ilike(f'%{query}%')) |
        (Book.isbn.ilike(f'%{query}%'))
    ).all()
    return jsonify(books_schema.dump(books)), 200

@app.errorhandler(NotFound)
def handle_not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(BadRequest)
def handle_bad_request(e):
    return jsonify({"error": "Bad request"}), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)