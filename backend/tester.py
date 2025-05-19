import app as backend
import os
from dotenv import load_dotenv

def main():
	load_dotenv(dotenv_path="../.env") 
	print("Performing tests...")

	with backend.app.test_client() as client:
		test_getAPIKey_isNotSet(client)
		test_getAPIKey_isSet(client)
		test_getArticles_noKeySet(client)
		test_getArticles_ableToGetArticles(client)
		test_getComments(client)
		test_post_comment(client)
		test_delete_comment(client)
		test_redact_comment(client)

def getAPIKey(client):
	response = client.get('/api/key')
	status = response.status_code
	key = response.get_json()['apiKey']
	return {'status': status, 'key': key}

def test_getAPIKey_isSet(client):
	print("Testing getAPIKey_isSet... ", end=" ")
	
	prevKey = os.getenv('NYT_API_KEY')
	os.environ["NYT_API_KEY"] = "random key"
	result = getAPIKey(client)
	
	if prevKey == None: del os.environ["NYT_API_KEY"]
	else: os.environ["NYT_API_KEY"] = prevKey

	if result['key'] == None:
		print("Failed!")
		print(
			"\tStatus code: {}\n\tGot [{}]"\
			.format(result['status'], result['key'])
		)
		return
	print("Passed!")

def test_getAPIKey_isNotSet(client):
	print("Testing getAPIKey_isNotSet... ", end=" ")

	prevKey = os.getenv('NYT_API_KEY')
	if prevKey != None: del os.environ["NYT_API_KEY"]
	result = getAPIKey(client)
	
	os.environ["NYT_API_KEY"] = prevKey

	if result['key'] != None:
		print("Failed!")
		print(
			"\tStatus code: {}\n\tGot [{}]"\
			.format(result['status'], result['key'])
		)
		return
	print("Passed!")


def test_getArticles_noKeySet(client):
	print("Testing getArticles_noKeySet...", end=" ")
	
	prevKey = os.getenv('NYT_API_KEY')
	if prevKey != None: del os.environ["NYT_API_KEY"]

	response = client.get('/api/articles')
	status = response.status_code
	data = response.get_json()	
	
	os.environ["NYT_API_KEY"] = prevKey
	
	if status != 500:
		print("Failed!")
		print("\tStatus code: {}".format(status))
		print("\tExpected: 500")
		return
	print("Passed!")

def test_getArticles_ableToGetArticles(client):
	print("Testing getArticles_ableToGetArticles...", end=" ")

	response = client.get('/api/testing/fetchArticles/\
		https://api.nytimes.com/svc/search/v2/articlesearch.json/\
		{}/\
		sacramento/\
		timesTag.location:"California"\
		'.format(os.getenv('NYT_API_KEY'))
	)

	status = response.status_code
	data = response.get_json()
	
	if data == []:
		print("Failed!")
		print("\tStatus code: {}".format(status))
		return
	print("Passed!")

def test_getComments(client):
    print("Testing get_comments...", end=" ")
    
    # Create a test comment
    comment = {
        'url': '[https://example.com](https://example.com)',
        'user': 'test@example.com',
        'text': 'This is a test comment',
        'timestamp': datetime.utcnow()
    }
    comments_collection.insert_one(comment)
    
    # Get comments for the test URL
    response = client.get('/api/comments?url=[https://example.com](https://example.com)')
    data = response.get_json()
    
    # Check if the comment is returned
    if len(data['comments']) != 1:
        print("Failed!")
        print("\tStatus code: {}".format(response.status_code))
        print("\tExpected: 1 comment, got {}".format(len(data['comments'])))
        return
    
    # Check if the comment data is correct
    if data['comments'][0]['_id'] != str(comment['_id']) or \
       data['comments'][0]['user'] != comment['user'] or \
       data['comments'][0]['text'] != comment['text']:
        print("Failed!")
        print("\tStatus code: {}".format(response.status_code))
        print("\tExpected: comment data to match, but got {}".format(data['comments'][0]))
        return
    
    print("Passed!")

def test_post_comment(client):
    print("Testing post_comment...", end=" ")


	response = client.get('/api/testing/fetchArticles/\
		https://api.nytimes.com/svc/search/v2/articlesearch.json/\
		{}/\
		sacramento/\
		timesTag.location:"California"\
		'.format(os.getenv('NYT_API_KEY'))
	)

	status = response.status_code
	data = response.get_json()
	
	if data == []:
		print("Failed!")
		print("\tStatus code: {}".format(status))
		return
	print("Passed!")

	
    
    # Set the user session
    with client.session_transaction() as session:
        session['user'] = {'email': 'test@example.com'}
    
    # Post a new comment
    data = {
        'url': '[https://example.com](https://example.com)',
        'text': 'This is a test comment'
    }
    response = client.post('/api/comments', json=data)
    data = response.get_json()
    
    # Check if the comment was created successfully
    if not data['success']:
        print("Failed!")
        print("\tStatus code: {}".format(response.status_code))
        print("\tExpected: success to be True, but got {}".format(data['success']))
        return
    
    # Check if the comment data is correct
    comment = comments_collection.find_one({'_id': ObjectId(data['comment']['_id'])})
    if comment['url'] != '[https://example.com](https://example.com)' or \
       comment['user'] != 'test@example.com' or \
       comment['text'] != 'This is a test comment':
        print("Failed!")
        print("\tStatus code: {}".format(response.status_code))
        print("\tExpected: comment data to match, but got {}".format(comment))
        return
    
    print("Passed!")

def test_delete_comment(client):
    print("Testing delete_comment...", end=" ")
    
    # Create a test comment
    comment = {
        'url': '[https://example.com](https://example.com)',
        'user': 'test@example.com',
        'text': 'This is a test comment',
        'timestamp': datetime.utcnow()
    }
    comments_collection.insert_one(comment)
    
    # Set the user session
    with client.session_transaction() as session:
        session['user'] = {'email': 'test@example.com'}
    
    # Delete the comment
    response = client.post('/api/comments/delete/{}'.format(comment['_id']), json={})
    data = response.get_json()
    
    # Check if the comment was deleted successfully
    if not data['success']:
        print("Failed!")
        print("\tStatus code: {}".format(response.status_code))
        print("\tExpected: success to be True, but got {}".format(data['success']))
        return
    
    # Check if the comment is no longer in the database
    if comments_collection.find_one({'_id': ObjectId(comment['_id'])}):
        print("Failed!")
        print("\tStatus code: {}".format(response.status_code))
        print("\tExpected: comment to be deleted, but it still exists")
        return
    
    print("Passed!")

def test_redact_comment(client):
    print("Testing redact_comment...", end=" ")
    
    # Create a test comment
    comment = {
        'url': '[https://example.com](https://example.com)',
        'user': 'test@example.com',
        'text': 'This is a test comment',
        'timestamp': datetime.utcnow()
    }
    comments_collection.insert_one(comment)
    
    # Set the user session
    with client.session_transaction() as session:
        session['user'] = {'email': 'moderator@hw3.com'}
    
    # Redact the comment
    response = client.patch('/api/comments/{}'.format(comment['_id']), json={'redact': True})
    data = response.get_json()
    
    # Check if the comment was redacted successfully
    if not data['success']:
        print("Failed!")

		

if __name__ == '__main__':
    main()
