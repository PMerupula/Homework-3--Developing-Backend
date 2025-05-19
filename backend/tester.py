import app as backend
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path="../.env") 

def main():
	print("Performing tests...")

	with backend.app.test_client() as client:
		test_getAPIKey_isNotSet(client)
		test_getAPIKey_isSet(client)
		test_getArticles_noKeySet(client)
		test_getArticles_ableToGetArticles(client)

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

if __name__ == '__main__':
    main()
