import json
import requests
import datetime
import os
import urllib


BOT_NAME = "TinderBot"
HEADERS = {
	"app_version"  : "4",
	"content-type" : "application/json",
	"platform"     : "android",
	"user-agent"   : "Tinder/4.0.9 (iPhone; iOS 8.1.1; Scale/2.00)",
}
HOST = "https://api.gotinder.com"
STORE_BASE_PATH = "{0}/tinderStore".format( os.environ["HOME"] )
TIME_FORMAT = "%H:%M:%S"


class TinderBotException( Exception ):
	pass


class TinderBot( object ):
	def __init__( self ):
		self.__headers = HEADERS
		self.__userId = 0
		self.__storePath = ""
		self.__recommendations = {}
		self.__matches = {}
		self.__blocks = {}

	def __loadRecommendations( self ):
		recommendationDirs = os.listdir( self.__storePath )
		for recommendationDir in recommendationDirs:
			profileFile = "{0}/{1}/profile.json".format( self.__storePath,
				recommendationDir )
			if not os.path.exists( profileFile ):
				continue
			with open(profileFile, "r") as inFile:
				recommendation = json.load( inFile )
				self.__recommendations[recommendation["_id"]] = recommendation
				msg = "{0}'s profile loaded.".format( recommendation["name"] )
				self.__printMsg( msg )
		self.__printMsg( "{0} recommendations loaded.".format(
			len( self.__recommendations ) ) )

	def getRecommendations( self ):
		return self.__recommendations

	def getMatched( self ):
		return self.__matches

	def __printMsg( self, msg ):
		time = datetime.datetime.now().strftime( TIME_FORMAT )
		msg = "[{0}] {1}: {2}".format( time, BOT_NAME, msg )
		print( msg )

	def authenticate( self, token, id_ ):
		data = json.dumps( {"facebook_token": token, "facebook_id": id_} )
		self.__printMsg( "Authenticating ..." )
		response = requests.post( "{0}/auth".format( HOST ),
			headers=self.__headers, data=data )
		if response.status_code != 200:
			# if 500 your facebook token might be out of date
			msg = "Cannot authenticate!: {0}".format( response.json() )
			self.__printMsg( msg )
			return
		self.__headers["X-Auth-Token"] = response.json()["token"]
		self.__userId = response.json()["user"]["_id"]
		self.__storePath = "{0}/{1}".format( STORE_BASE_PATH, self.__userId )
		self.__printMsg( "Athentication succesfully." )
		self.__loadRecommendations()

	def __saveProfile( self, recommendation, profileDir ):
		profileDestination = "{0}/profile.json".format( profileDir )
		self.__printMsg( "Saving {0}'s profile ...".format( recommendation["name"] ) )
		with open(profileDestination, "w") as outFile:
			json.dump( recommendation, outFile )
	
	def __savePhotos( self, recommendation, photosDir ):
		self.__printMsg( "Saving {0}'s photos ...".format( recommendation["name"] ) )
		for photo in recommendation["photos"]:
			url = photo["url"]
			photoname = url.rsplit( "/", 1 )[1]
			photoDestination = "{0}/{1}".format( photosDir, photoname )
			urllib.request.urlretrieve( url, photoDestination )

	def __saveIndex( self, recommendation, indexDir, photosDir ):
		self.__printMsg( "Indexing {0} ...".format( recommendation["name"] ) )
		if not recommendation["photos"]:
			self.__printMsg( "Cannot save index for {0}: No pictures.".format(
				recommendation["name"] ) )
			return
		photoname = recommendation["photos"][0]["url"].rsplit( "/", 1 )[1]
		photoDestination = "{0}/{1}".format( photosDir, photoname )
		_, extension = os.path.splitext( photoname )
		indexLink = "{0}/{1}_{2}{3}".format( indexDir, recommendation["name"],
			recommendation["_id"], extension )
		if os.path.exists( indexLink ):
			os.remove( indexLink )
		os.symlink( photoDestination, indexLink )

	def __saveRecommendation( self, recommendation ):
		# Profile
		profileDir = "{0}/{1}_{2}".format( self.__storePath, recommendation["name"],
			recommendation["_id"] )
		if not os.path.isdir( profileDir ):
			os.makedirs( profileDir )
		self.__saveProfile( recommendation, profileDir )
		# Photos
		photosDir = "{0}/{1}_{2}/photos".format( self.__storePath, recommendation["name"],
			recommendation["_id"] )
		if not os.path.isdir( photosDir ):
			os.makedirs( photosDir )
		self.__savePhotos( recommendation, photosDir )
		# Index
		indexDir = "{0}/index".format( self.__storePath )
		if not os.path.isdir( indexDir ):
			os.makedirs( indexDir )
		self.__saveIndex( recommendation, indexDir, photosDir )
	
	def __getPingTime( self, recommendation ):
		pingTimeString = recommendation["ping_time"].split( ".", 1)[0]
		pingTime = datetime.datetime.strptime( pingTimeString,
			"%Y-%m-%dT%H:%M:%S" )
		return pingTime

	def __updateRecommendation( self, recommendation ):
		id_ = recommendation["_id"]
		name = recommendation["name"]
		if id_ in self.__recommendations:
			savedPingTime = self.__getPingTime( self.__recommendations[id_] )
			newPingTime = self.__getPingTime( recommendation )
			if newPingTime > savedPingTime:
				self.__printMsg( "Updating {0} in the store:".format( name ) )
				self.__saveRecommendation( recommendation )
				self.__recommendations[id_] = recommendation
				self.__printMsg( "{0} updated.".format( name ) )
			else:
				msg = "{0} is up to date in the store.".format( name )
				self.__printMsg( msg )
		else:
			self.__printMsg( "Adding {0} to the store:".format( name ) )
			self.__saveRecommendation( recommendation )
			self.__recommendations[id_] = recommendation
			self.__printMsg( "{0} added.".format( name ) )
				
	def requestRecommendations( self ):
		self.__printMsg( "Requesting recommendations ..." )
		response = requests.get( "{0}/user/recs".format( HOST ),
			headers=self.__headers )
		if response.status_code != 200:
			msg = "{0}: Error in request: {1}".format( BOTNAME,
				response.status_code )
			raise TinderBotException( msg )
		recommendations = response.json()["results"]
		self.__printMsg( "{0} recommendations:".format(
			len( recommendations ) ) )
		for recommendation in recommendations:
			self.__updateRecommendation( recommendation )
		self.__printMsg( "{0} total  recommendations.".format(
			len( self.__recommendations ) ) )

	def requestUpdates( self ):
		data = json.dumps( {"last_activity_date": ""} )
		response = requests.post( "{0}/updates".format( HOST ),
			headers=self.__headers, data=data )
		if response.status_code != 200:
			msg = "{0}: Error in request: {1}".format( BOTNAME,
				response.status_code )
			raise TinderBotException( msg )
		responseDict = response.json()
		self.__matches = responseDict["matches"]
		self.__blocks = reponseDict["blocks"]

	def likeRecommendations( self ):
		pass
