from flask import Flask, jsonify, send_from_directory, request
import os
import requests # We import the requests library to make HTTP requests to the NYT API
from flask_cors import CORS

from flask import Flask, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token

from bson.objectid import ObjectId

# loads environment variables from .env file
from dotenv import load_dotenv
load_dotenv(dotenv_path="./.env")

static_path = os.getenv('STATIC_PATH','static')
template_path = os.getenv('TEMPLATE_PATH','templates')

app = Flask(__name__, static_folder=static_path, template_folder=template_path)
app.secret_key = os.urandom(24)

oauth = OAuth(app)
nonce = generate_token()

client_name = os.getenv('OIDC_CLIENT_NAME')

oauth.register(
    name=os.getenv('OIDC_CLIENT_NAME'),
    client_id=os.getenv('OIDC_CLIENT_ID'),
    client_secret=os.getenv('OIDC_CLIENT_SECRET'),
    #server_metadata_url='http://dex:5556/.well-known/openid-configuration',
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

CORS(app)

# Defined so that we can just call NYT_API_KEY instead of os.getenv('NYT_API_KEY')
NYT_API_KEY = os.getenv('NYT_API_KEY')

@app.route('/api/key')
def get_key():
    NYT_API_KEY = os.getenv('NYT_API_KEY')  # added because tester.py doesn't call the global version on line 17
    return jsonify({'apiKey': NYT_API_KEY})

# API route that queries the NYT Article Search API for articles related to either Sacramento or Davis, and returns the data.
@app.route('/api/articles')
def get_articles():
    NYT_API_KEY = os.getenv('NYT_API_KEY')  # added because tester.py doesn't call the global version on line 17
    page = request.args.get('page', 0, type=int)
    # Passes the page number to the NYT API (this is for the extra credit requirement of infinite scrolling)

    # Returns an error response if the NYT API key isn't found
    if NYT_API_KEY == None:
        return jsonify({'error': 'NYT API key not found'}), 500
    
    # The endpoint for the NYT Article Search API
    nyt_url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
    all_articles = []

    # We tried different combinations of Sacramento and Davis, but the best results were obtained by querying them separately.
    # We also found that using the default sort order (best) seemed to give us the desired output for both, while newest gave us somewhat inaccurate results.
    try:
        """
        By default, the NYT API has a limit of 10 articles per fetch. Since we have 2 fetches (one per city), we can get a maximum of 20 articles.
        Instead of trying to get all the articles at once, in order to satisfy the extra credit requirement of infinite scrolling, we shall make a new request every time the user scrolls down, which will fetch the next 10 (or technically 20) articles.
        A timeout of 30 seconds is set in order to avoid being stuck forever.
        Each request is made, and if successful, gets the json response and stores articles in a list temporarily before adding it to the overall list.
        .extend() lets us skip having to do a for loop with a .append() for each article.
        """
        # First fetch: Sacramento
        sac_articles = fetchArticlesFromLocation(nyt_url, NYT_API_KEY, 'sacramento', 'timesTag.location:"California"')
        all_articles.extend(sac_articles)

        # Second fetch: Davis
        davis_articles = fetchArticlesFromLocation(nyt_url, NYT_API_KEY, 'davis', 'timesTag.organization:"University of California, Davis"')
        all_articles.extend(davis_articles)

        # Since we have all the Davis and Sacramento articles in the same list, we now sort them by the publication date.
        combined_articles = sorted(
            all_articles,
            key=lambda x: x.get('pub_date', ''),
            reverse=True # To ensure that the first articles are the most recent ones
        )

        # We don't need all of the information from the articles for our frontend, so we'll prune the data to only include the fields we need.
        simplified_articles = trimArticleData(combined_articles)
        return jsonify({'articles': simplified_articles})
    
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/user')
def get_user():
    user = session.get('user')
    if user:
        email = user.get('email')
        role = ROLE_MAP.get(email, 'user')  # Default to 'user' if not found
        return jsonify({
            'user': {
                'email': email,
                'role': role
            }
        })
    else:
        return jsonify({'user': None})

@app.route('/api/testing/fetchArticles/<path:siteUrl>/<apiKey>/<question>/<fullerQuestion>')
def fetchArticlesFromLocation(siteUrl:str, apiKey:str, question:str, fullerQuestion:str):
    response = None

    try:
        response = requests.get(siteUrl, params={
            'q': question,
            'fq': fullerQuestion,
            'api-key': apiKey
        }, timeout=30)
    except requests.RequestException as e:
        return e
    
    if response.status_code == requests.codes.ok:
        data = response.json()
        articles = data.get('response', {}).get('docs', [])
        return articles
    
    return []

def trimArticleData(sourceArticles:list):
    # We don't need all of the information from the articles for our frontend, so we'll prune the data to only include the fields we need.
    trimmedArticles = []

    for article in sourceArticles:
        # We need the article headline, of course.
        headline = article.get('headline', {}).get('main', '')
        # The abstract is a brief summary of the article. The actual contents we can just link to.
        abstract = article.get('abstract', '')
        # We need the URL to link to the article.
        url = article.get('web_url', '')
        # We need to show when the article was written.
        pub_date = article.get('pub_date', '')
        # Credit to the New York Times. Likely unnecessary since it's implied, but I'll add it for legal reasons.
        source = article.get('source', '')
        
        # We need to display an image for the article. There's a multimedia field containing a list of images, but we only need one for the preview.
        image_url = None
        multimedia = article.get('multimedia')
        
        # Multimedia field can be a list or a dict, so we'll check both and act accordingly.
        if isinstance(multimedia, dict):
            # If it's a dict, we can just check to see if there's a default or thumbnail image defined, since that's what the article would have used in the NYT.
            if 'default' in multimedia and 'url' in multimedia['default']:
                image_url = multimedia['default']['url']
            elif 'thumbnail' in multimedia and 'url' in multimedia['thumbnail']:
                image_url = multimedia['thumbnail']['url']
        
        # If it's a list, we just pick the largest element for ideal visual clarity.
        # It being a list indicates there's no one image defined as the thumbnail/default image.
        elif isinstance(multimedia, list) and multimedia:
            # Pick the largest image from the list
            valid_images = []
            for m in multimedia:
                # If the image has a width and height, it's valid
                if m.get('width') and m.get('height'):
                    valid_images.append(m)
            # If there are any valid images, find and pick the largest one
            if(valid_images):
                largest = max(valid_images, key=lambda m: m['width'] * m['height'])
            # If there's no valid images, we don't have an image to show
            else:
                largest = None
            if largest:
                # if the image URL already starts with http, that means we can just directly use it
                if largest['url'].startswith('http'):
                    image_url = largest['url']
                # Otherwise, we need to prepend the NYT image URL to the url that we've ascertained
                else:
                    image_url = f"https://static01.nyt.com/{largest['url']}"
        
        # Append the extracted data to the trimmedArticles list
        trimmedArticles.append({
            'headline': headline,
            'abstract': abstract,
            'url': url,
            'pub_date': pub_date,
            'source': source,
            'image_url': image_url
        })

    return trimmedArticles


comments_by_url = {}  # Dictionary mapping article URL to list of comments


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

    user_info = oauth.flask_app.parse_id_token(token, nonce=nonce)  # or use .get('userinfo').json()
    session['user'] = user_info
    #return redirect('/')
    return redirect('http://localhost:5173') # For development 

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/<path:path>')
def serve_frontend(path=''):
    if path != '' and os.path.exists(os.path.join(static_path,path)):
        return send_from_directory(static_path, path)
    return send_from_directory(template_path, 'index.html')

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)),debug=debug_mode)

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI")
mongo = MongoClient(MONGO_URI)
db = mongo["mydatabase"]
comments_collection = db["comments"]

@app.route('/api/comments', methods=['GET'])
def get_comments():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing article URL'}), 400

    # Get comments for this article
    comment_docs = comments_collection.find({'url': url})
    comment_list = []
    for c in comment_docs:
        comment_list.append({
            '_id': str(c.get('_id')),
            'user': c.get('user'),
            'username': c.get('username'),  # Optional
            'text': c.get('text'),
            'timestamp': c.get('timestamp')  # Optional
        })

    return jsonify({'comments': comment_list})

from datetime import datetime

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
        'user': user['username'],
        'text': text,
        'timestamp': datetime.utcnow()
    }

    result = comments_collection.insert_one(comment)
    comment['_id'] = str(result.inserted_id)  # Include the inserted ID as a string

    return jsonify({'success': True, 'comment': comment})

from bson.objectid import ObjectId
from flask import abort

def is_moderator():
    user = session.get('user')
    return user and user.get('email') in ['moderator@hw3.com', 'admin@hw3.com']

@app.route('/api/comments/delete/<comment_id>', methods=['POST'])
def delete_comment(comment_id):
    user = session.get('user')
    if not user or user['email'] not in ['admin@hw3.com', 'moderator@hw3.com']:
        return jsonify({'error': 'Unauthorized'}), 401

    comment = comments_collection.find_one({'_id': ObjectId(comment_id)})
    if not comment:
        return jsonify({'error': 'Comment not found'}), 404

    # Prevent moderators from deleting other moderators' or admin's comments
    author_email = comment.get('user')
    if author_email in ['admin@hw3.com', 'moderator@hw3.com'] and user['email'] != author_email:
        return jsonify({'error': 'Cannot delete comments by other moderators/admins'}), 403

    # Perform the soft delete
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