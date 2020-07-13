### anilist.co ###
# API exemple:  https://anilist.co/graphiql?query=%7B%0A%20%20anime%3A%20Media(idMal%3A%2023273%2C%20type%3A%20ANIME)%20%7B%0A%20%20%20%20title%20%7B%0A%20%20%20%20%20%20english%0A%20%20%20%20%7D%0A%20%20%20%20coverImage%20%7B%0A%20%20%20%20%20%20url%3A%20extraLarge%0A%20%20%20%20%7D%0A%20%20%7D%0A%7D%0A

### Imports ###
# Python Modules #
import os
# HAMA Modules #
import common
from common import Log, DictString, Dict, SaveDict # Direct import of heavily used functions

### Variables ###
ARM_SERVER_URL = "https://relations.yuna.moe/api/ids?source=anidb&id={id}"

GRAPHQL_API_URL = "https://graphql.anilist.co"
ANIME_DATA_DOCUMENT = """
query($id: Int, $malId: Int) {
  anime: Media(type: ANIME, id: $id, idMal: $malId) {
    id,
    title {
      romaji
      english
      native
      userPreferred
    },
    averageScore,
    startDate {
      year
      month
      day
    },
    genres,
    status,
    coverImage {
      url: extraLarge
    }
    bannerImage
  }
}
""".strip()

### Functions ###
def MakeGraphqlQuery(document, variables):
  Log.Info("Query: {}".format(document))
  Log.Info("Variables: {}".format(variables))

  source   = variables.keys()[0]
  data     = JSON.StringFromObject({"query": document, "variables": variables})
  response = common.LoadFile(filename=str(variables[source])+'.json', relativeDirectory=os.path.join('AniList', 'json', source), url=GRAPHQL_API_URL, data=data, cache=CACHE_1DAY)

  # EX: {"data":null,"errors":[{"message":"Not Found.","hint":"Use POST request to access graphql subdomain.","status":404}]}
  if len(Dict(response, 'errors', default=[])) > 0:
    Log.Error("Got error: {}".format(Dict(response, 'errors')[0]))
    return None

  return Dict(response, "data")

def GetMetadata(AniDBid, MALid):
  Log.Info("=== AniList.GetMetadata() ===".ljust(157, '='))
  AniList_dict = {}

  # Try to match the AniDB id to an AniList id as it has a higher chance of being correct
  ALid = Dict(common.LoadFile(filename=AniDBid+'.json', relativeDirectory=os.path.join('AniList', 'json', 'AniDBid'), url=ARM_SERVER_URL.format(id=AniDBid)), "anilist", default=None)

  Log.Info("AniDBid={}, MALid={}, ALid={}".format(AniDBid, MALid, ALid))
  if not MALid or not MALid.isdigit(): return AniList_dict

  Log.Info("--- series ---".ljust(157, "-"))

  # Use the AniList id if we got one, but fall back to the MAL id
  variables = {}
  if ALid is not None:  SaveDict(ALid,       variables, "id"   )
  else:                 SaveDict(int(MALid), variables, "malId")

  # Fetch data
  data = MakeGraphqlQuery(ANIME_DATA_DOCUMENT, variables)

  if data:
    titles = Dict(data, "anime", "title")
    if titles:
      title, original_title, language_rank = GetAniListTitle(titles)
      Log.Info("[ ] language_rank: {}" .format(SaveDict(language_rank,            AniList_dict, 'language_rank')))
      Log.Info("[ ] title: {}"         .format(SaveDict(title,                    AniList_dict, 'title')))
      Log.Info("[ ] original_title: {}".format(SaveDict(original_title,           AniList_dict, 'original_title')))

    rating = Dict(data, "anime", "averageScore")
    if rating:
      Log.Info("[ ] rating: {}" .format(SaveDict(float(rating) / 10,              AniList_dict, 'rating')))

    startDate = Dict(data, "anime", "startDate")
    if startDate:
      startDateString = str(Dict(startDate, "year")) + '-' + str(Dict(startDate, "month")).zfill(2) + '-' + str(Dict(startDate, "day")).zfill(2)
      Log.Info("[ ] originally_available_at: {}".format(SaveDict(startDateString, AniList_dict, 'originally_available_at')))

    genres = Dict(data, "anime", "genres")
    if genres:
      Log.Info("[ ] genres: {}".format(SaveDict(sorted(genres),                   AniList_dict, 'genres')))

    status = Dict(data, "anime", "status")
    if status:
      if status == 'RELEASING':
        Log.Info("[ ] status: {}".format(SaveDict("Continuing",                   AniList_dict, 'status')))
      elif status == 'FINISHED':
        Log.Info("[ ] status: {}".format(SaveDict("Ended",                        AniList_dict, 'status')))

    Log.Info("--- images ---".ljust(157, "-"))

    posterUrl = Dict(data, "anime", "coverImage", "url")
    if posterUrl:
      Log.Info("[ ] poster: {}".format(SaveDict((os.path.join('AniList', 'poster',  os.path.basename(posterUrl)), common.poster_rank('AniList', 'posters'), None), AniList_dict, 'posters', posterUrl)))

    bannerUrl = Dict(data, "anime", "bannerImage")
    if bannerUrl:
      Log.Info("[ ] banner: {}".format(SaveDict((os.path.join('AniList', 'banners', os.path.basename(bannerUrl)), common.poster_rank('AniList', 'banners'), None), AniList_dict, 'banners', bannerUrl)))

  Log.Info("--- return ---".ljust(157, '-'))
  Log.Info("AniList_dict: {}".format(DictString(AniList_dict, 4)))
  return AniList_dict

def GetAniListTitle(titles):
	languages = [language.strip() for language in Prefs['SerieLanguagePriority'].split(',')] #[ Prefs['SerieLanguage1'], Prefs['SerieLanguage2'], Prefs['SerieLanguage3'] ]  #override default language
	if not 'main' in languages:  languages.append('main')                                    # Add main to the selection if not present in list (main nearly same as x-jat)
	langTitles    = ["" for index in range(len(languages))]                                  # languages: title order including main title, then choosen title

	for lang in languages:
		if lang == 'main' or lang == 'x-jat':
			langTitles[languages.index(lang)] = Dict(titles, "romaji")
		if lang == 'en':
			langTitles[languages.index(lang)] = Dict(titles, "english")
		if lang == 'ja':
			langTitles[languages.index(lang)] = Dict(titles, "native")

	for index, item in enumerate(langTitles+[]):
		if item: break

	return langTitles[index], langTitles[languages.index('main') if 'main' in languages else 1 if 1 in langTitles else 0], index 