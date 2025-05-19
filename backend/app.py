from flask import Flask, jsonify, send_from_directory, request, redirect, session
import os
import requests
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token
from dotenv import load_dotenv
from datetime import datetime
from bson.objectid import ObjectId
from pymongo import MongoClient

# === Load environment variables ===
load_dotenv(dotenv_path="./.env")

# === Flask app setup ===
static_path = os.getenv('STATIC_PATH', 'static')
template_path = os.getenv('TEMPLATE_PATH', 'templates')
app = Flask(__name__, static_folder=static_path, template_folder=template_path)
app.secret_key = os.urandom(24)
CORS(app)

# === OAuth setup ===
oauth = OAuth(app)
nonce = generate_token()

client_name = os.getenv('OIDC_CLIENT_NAME')

oauth.register(
    name=client_name,
    client_id=os.getenv('OIDC_CLIENT_ID'),
    client_secret=os.getenv('OIDC_CLIENT_SECRET'),
    authorization_endpoint="http://localhost:5556/auth",
    token_endpoint="http://dex:5556/token",
    jwks_uri="http://dex:5556/keys",
    userinfo_endpoint="http://dex:5556/userinfo",
    device_authorization_endpoint="http://dex:5556/device/code",
    client_kwargs={'scope': 'openid email profile'}
)

ROLE_MAP = {
    'admin@hw3.com': 'moderator',
    'moderator@hw3.com': 'moderator',
    'user@hw3.com': 'user'
}

# === MongoDB Setup ===
MONGO_URI = os.getenv("MONGO_URI")
mongo = MongoClient(MONGO_URI)
db = mongo["mydatabase"]
comments_collection = db["comments"]

# === NYT API key ===
NYT_API_KEY = os.getenv('NYT_API_KEY')

@app.route('/api/key')
def get_key():
    return jsonify({'apiKey': NYT_API_KEY})

@app.route('/api/articles')
def get_articles():
    page = request.args.get('page', 0, type=int)
    if not NYT_API_KEY:
        return jsonify({'error': 'NYT API key not found'}), 500

    nyt_url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
    all_articles = []

    try:
        sac_articles = fetchArticlesFromLocation(nyt_url, NYT_API_KEY, 'sacramento', 'timesTag.location:"California"')
        davis_articles = fetchArticlesFromLocation(nyt_url, NYT_API_KEY, 'davis', 'timesTag.organization:"University of California, Davis"')
        all_articles.extend(sac_articles)
        all_articles.extend(davis_articles)

        combined_articles = sorted(all_articles, key=lambda x: x.get('pub_date', ''), reverse=True)
        simplified_articles = trimArticleData(combined_articles)
        return jsonify({'articles': simplified_articles})
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user')
def get_user():
    user = session.get('user')
    if user:
        email = user.get('email')
        role = ROLE_MAP.get(email, 'user')
        return jsonify({'user': {
            'email': email,
            'username': user.get('name') or email.split('@')[0],
            'role': role
        }})
    return jsonify({'user': None})

@app.route('/api/comments', methods=['GET'])
def get_comments():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing article URL'}), 400

    comment_docs = comments_collection.find({'url': url})
    comment_list = []
    for c in comment_docs:
        comment_list.append({
            '_id': str(c.get('_id')),
            'user': c.get('user'),
            'username': c.get('username'),
            'text': c.get('text'),
            'timestamp': c.get('timestamp')
        })

    return jsonify({'comments': comment_list})

@app.route('/api/comments', methods=['POST'])
def post_comment():
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    url = data.get('url')
    text = data.get('text')

    if not url or not text:
        return jsonify({'error': 'Missing url or text'}), 400

    comment = {
        'url': url,
        'user': user['email'],
        'username': user.get('name') or user['email'].split('@')[0],
        'text': text,
        'timestamp': datetime.utcnow()
    }

    result = comments_collection.insert_one(comment)
    comment['_id'] = str(result.inserted_id)

    return jsonify({'success': True, 'comment': comment})

@app.route('/api/comments/delete/<comment_id>', methods=['POST'])
def delete_comment(comment_id):
    user = session.get('user')
    if not user or user['email'] not in ['admin@hw3.com', 'moderator@hw3.com']:
        return jsonify({'error': 'Unauthorized'}), 401

    comment = comments_collection.find_one({'_id': ObjectId(comment_id)})
    if not comment:
        return jsonify({'error': 'Comment not found'}), 404

    if comment.get('user') in ['admin@hw3.com', 'moderator@hw3.com'] and user['email'] != comment.get('user'):
        return jsonify({'error': 'Cannot delete comments by other moderators/admins'}), 403

    result = comments_collection.update_one(
        {'_id': ObjectId(comment_id)},
        {'$set': {'text': 'Comment was removed by a moderator'}}
    )

    return jsonify({'success': result.modified_count == 1})

@app.route('/api/comments/<comment_id>', methods=['PATCH'])
def redact_comment(comment_id):
    user = session.get('user')
    if not user or user['email'] not in ['admin@hw3.com', 'moderator@hw3.com']:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    new_text = data.get('text')

    if not new_text:
        return jsonify({'error': 'Missing redacted text'}), 400

    result = comments_collection.update_one(
        {'_id': ObjectId(comment_id)},
        {'$set': {'text': new_text}}
    )

    if result.matched_count == 0:
        return jsonify({'error': 'Comment not found'}), 404

    return jsonify({'success': True})

@app.route('/')
@app.route('/login')
def login():
    session['nonce'] = nonce
    redirect_uri = 'http://localhost:8000/authorize'
    return oauth.flask_app.authorize_redirect(redirect_uri, nonce=nonce)

@app.route('/authorize')
def authorize():
    token = oauth.flask_app.authorize_access_token()
    nonce = session.get('nonce')
    user_info = oauth.flask_app.parse_id_token(token, nonce=nonce)
    session['user'] = user_info
    return redirect('http://localhost:5173')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/<path:path>')
def serve_frontend(path=''):
    if path != '' and os.path.exists(os.path.join(static_path, path)):
        return send_from_directory(static_path, path)
    return send_from_directory(template_path, 'index.html')

@app.route('/api/testing/fetchArticles/<path:siteUrl>/<apiKey>/<question>/<fullerQuestion>')
def fetchArticlesFromLocation(siteUrl: str, apiKey: str, question: str, fullerQuestion: str):
    try:
        response = requests.get(siteUrl, params={
            'q': question,
            'fq': fullerQuestion,
            'api-key': apiKey
        }, timeout=30)
        if response.status_code == requests.codes.ok:
            return response.json().get('response', {}).get('docs', [])
    except requests.RequestException as e:
        return e
    return []

def trimArticleData(sourceArticles: list):
    trimmedArticles = []
    for article in sourceArticles:
        headline = article.get('headline', {}).get('main', '')
        abstract = article.get('abstract', '')
        url = article.get('web_url', '')
        pub_date = article.get('pub_date', '')
        source = article.get('source', '')
        image_url = None
        multimedia = article.get('multimedia')

        if isinstance(multimedia, dict):
            if 'default' in multimedia and 'url' in multimedia['default']:
                image_url = multimedia['default']['url']
            elif 'thumbnail' in multimedia and 'url' in multimedia['thumbnail']:
                image_url = multimedia['thumbnail']['url']
        elif isinstance(multimedia, list) and multimedia:
            valid_images = [m for m in multimedia if m.get('width') and m.get('height')]
            if valid_images:
                largest = max(valid_images, key=lambda m: m['width'] * m['height'])
                if largest['url'].startswith('http'):
                    image_url = largest['url']
                else:
                    image_url = f"https://static01.nyt.com/{largest['url']}"

        trimmedArticles.append({
            'headline': headline,
            'abstract': abstract,
            'url': url,
            'pub_date': pub_date,
            'source': source,
            'image_url': image_url
        })
    return trimmedArticles

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=debug_mode)