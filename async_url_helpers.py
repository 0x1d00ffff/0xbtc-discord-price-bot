import aiohttp

async def get_json_from_url(url, parameters=None, headers=None, invalid_mimetype_to_allow=None):
    """
    Load and parse json at a url
    
    :type       url:                        str
    :param      url:                        URL to load
    :type       parameters:                 dict
    :param      parameters:                 Dict of optional GET parameters
    :type       headers:                    dict
    :param      headers:                    Dict of optional header values
    :type       invalid_mimetype_to_allow:  str
    :param      invalid_mimetype_to_allow:  If set, decode JSON that is downloaded
                                            with this mimetype. Otherwise expect a
                                            json mimetype.
    
    :returns:   The json from url.
    :rtype:     dict
    
    :raises     TimeoutError:               Raised on errors communicating with
                                            server
    """
    result = None
    default_header = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
    }

    if headers is None:
        headers = default_header
    else:
        for key in default_header:
            headers.setdefault(key, default_header[key])

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, params=parameters) as response:
                if response.status == 200:
                    result = await response.json(content_type=invalid_mimetype_to_allow)
                else:
                    raise TimeoutError("api is down - got http status {}".format(response.status))
    except ConnectionError:
        raise TimeoutError("api is down - got timeout")
    except aiohttp.client_exceptions.ContentTypeError as e:
        raise TimeoutError("api responded with unexpected content type ({})".format(e))

    return result

    # NOTE: previously, this function checked for values in the response
    #       if there was an error decoding the json. may need to reimplement.

    # try:
    #     data = json.loads(response.text)
    # except json.decoder.JSONDecodeError:
    #     response = response[:2000]
    #     if ("be right back" in response
    #         or "404 Not Found" in response and "nginx" in response
    #         or "Request unsuccessful. Incapsula incident ID" in response):
    #         raise TimeoutError("api is down - got error page")
    #     else:
    #         raise TimeoutError("api sent bad data ({})".format(repr(response)))
    # else:
    #     return data

