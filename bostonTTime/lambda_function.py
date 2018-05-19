"""
This sample demonstrates a simple skill built with the Amazon Alexa Skills Kit.
The Intent Schema, Custom Slots, and Sample Utterances for this skill, as well
as testing instructions are located at http://amzn.to/1LzFrj6

For additional samples, visit the Alexa Skills Kit Getting Started guide at
http://amzn.to/1LGWsLG
"""

from __future__ import print_function
import urllib2
import datetime
import json
import pytz
import dateutil.parser

# ----------- NOTES on API calls -----------
# Filter routes for ID ("Red", "Green-E", etc): 
#           routes/?filter%5Bid%5D={id}
# Prediction by stop ID and line ("place-dwnxg" and "Orange"):
#           predictions/?filter%5Bstop%5D={stop}&filter%5Broute%5D={line}
# Find all stops for a line:
#           stops/?fields%5Bstop%5D=name&filter%5Broute%5D={line}


# Basic request necessities
url = "https://api-v3.mbta.com"  # base url
predictions_url = url + "/predictions"  # url for predictions
routes_url = url + "/routes"
stops_url = url + "/stops"
api_key = "22fe3c7f0b354f608344baf15601c305"  # API key for MBTA API v3
default_sort = "arrival-time"  # sort by closest arrival



# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "What's up Casey? You big dumb idiot ha ha ha"
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = ""
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you for using Boston Train Party. " \
                    "Have a nice day! "
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))

def build_route_url(route):
    global routes_url
    url = routes_url + "/" + route
    return url

def build_stop_url(route):
    global stops_url
    url = stops_url + "/?fields%5Bstop%5D=name&filter%5Broute%5D=" + route
    return url

def build_prediction_url(stop, route):
    global predictions_url
    url = predictions_url + "/?fields%5Bprediction%5D=arrival_time,direction_id&" + \
        "filter%5Bstop%5D=" + stop + "&filter%5Broute%5D=" + route + "&sort=arrival_time"
    url += "&page%5Blimit%5D=5"
    print(url)
    return url

def create_prediction_string(prediction):
    arrival_time = dateutil.parser.parse(prediction['attributes']['arrival_time'])
    arrival_time = arrival_time.replace(tzinfo=pytz.utc) - arrival_time.utcoffset()
    delta = arrival_time - datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    delta_str = ""
    if delta.days < 0:
        delta_str = "boarding"
    elif delta.seconds <= 60:
        delta_str = str(delta.seconds) + " seconds away"
    else:
        delta_str = str(int(delta.seconds / 60))
        if delta_str == "1":
            delta_str += " minute away"
        else:
            delta_str += " minutes away"
    return delta_str

def build_direction_prediction(prediction_response_data, route_dirs, stop, route, dir):
    prediction_index = -1
    for i, p in enumerate(prediction_response_data):
        if p['attributes']['direction_id'] == dir:
            prediction_index = i
            break
    if prediction_index > -1:
        delta_str = create_prediction_string(prediction_response_data[prediction_index])
        output = "The next " + route_dirs[dir] + " " + route + " line is " + \
                    delta_str + " from " + stop + "."
    else:
        output = "There are no scheduled " + route_dirs[dir] + " "+  route + \
                    " trains at this time."
    return output

def find_train_time(intent, session):
    """ 
    """
    card_title = intent['name']
    should_end_session = True

    if ('route' in intent['slots'] and  'stop' in intent['slots']) and \
        ('resolutions' in intent['slots']['route'] and 'resolutions' in intent['slots']['stop']):
        route = intent['slots']['route']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name']
        stop = intent['slots']['stop']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name']

        # Find direction info
        dir_response = urllib2.urlopen(build_route_url(route))
        dir_response_data = json.loads(dir_response.read())['data']
        route_dirs = dir_response_data['attributes']['direction_names']

        # Find the stop ID
        stop_response = urllib2.urlopen(build_stop_url(route))
        stop_response_data = json.loads(stop_response.read())['data']
        stop_id = ""
        for stop_data in stop_response_data:
            if stop == stop_data['attributes']['name']:
                stop_id = stop_data['id']
                break

        prediction_response = urllib2.urlopen(build_prediction_url(stop_id, route))
        prediction_response_data = json.loads(prediction_response.read())['data']
        speech_output = build_direction_prediction(prediction_response_data, route_dirs, stop, route, 0)
        speech_output += " "
        speech_output += build_direction_prediction(prediction_response_data, route_dirs, stop, route, 1)
    else:
        speech_output = "Please include the direction, route, and stop you are looking for. "
    reprompt_text = ""
    print(speech_output)
    return build_response({}, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "TrainTimeAway":
        return find_train_time(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])



testJson = {
    "version": "1.0",
    "session": {
        "new": True,
        "sessionId": "amzn1.echo-api.session.13c9fead-1fdc-417d-a683-d638ccfedfc2",
        "application": {
            "applicationId": "amzn1.ask.skill.489c1bc5-928a-436e-93d1-6edf0d25d6e3"
        },
        "user": {
            "userId": "amzn1.ask.account.AGWUUA2FK26XASDV6RLWXZJNC4BQ2CCXKMFFIKAZRKDNX23E3WIEZIOX2I52RMYCJKBA5BCAGJHKCMUFJ42R2YHDPLJ5IOW7WRYEN7RZN6GSJ6KDA4FRTQFANSXFWDXSM3I3UMHNA2LYEWYTRNDO6BQGLTOXM3ZJQRVHQKEGK4FONBFGANV5S7D6SEIRPRZ46FFULNWYZMMWCPI"
        }
    },
    "context": {
        "AudioPlayer": {
            "playerActivity": "IDLE"
        },
        "Display": {},
        "System": {
            "application": {
                "applicationId": "amzn1.ask.skill.489c1bc5-928a-436e-93d1-6edf0d25d6e3"
            },
            "user": {
                "userId": "amzn1.ask.account.AGWUUA2FK26XASDV6RLWXZJNC4BQ2CCXKMFFIKAZRKDNX23E3WIEZIOX2I52RMYCJKBA5BCAGJHKCMUFJ42R2YHDPLJ5IOW7WRYEN7RZN6GSJ6KDA4FRTQFANSXFWDXSM3I3UMHNA2LYEWYTRNDO6BQGLTOXM3ZJQRVHQKEGK4FONBFGANV5S7D6SEIRPRZ46FFULNWYZMMWCPI"
            },
            "device": {
                "deviceId": "amzn1.ask.device.AHSICQAKKLVYXNXN66H3RTQPUAHGJPUQXG4VB2DCR6GM2BQVJFBEY2XX7TFNH5QYJSRBS52F3A2WHXQ7YZQF7ZZHSE7IOIBVMLGXX7WPYUU6M4YBT7MGIKOJWDVFN5OY4UAEOHGYDMGHR4SIPCUBBU3LPY6A",
                "supportedInterfaces": {
                    "AudioPlayer": {},
                    "Display": {
                        "templateVersion": "1.0",
                        "markupVersion": "1.0"
                    }
                }
            },
            "apiEndpoint": "https://api.amazonalexa.com",
            "apiAccessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjEifQ.eyJhdWQiOiJodHRwczovL2FwaS5hbWF6b25hbGV4YS5jb20iLCJpc3MiOiJBbGV4YVNraWxsS2l0Iiwic3ViIjoiYW16bjEuYXNrLnNraWxsLjQ4OWMxYmM1LTkyOGEtNDM2ZS05M2QxLTZlZGYwZDI1ZDZlMyIsImV4cCI6MTUyNjcwMTA0MCwiaWF0IjoxNTI2Njk3NDQwLCJuYmYiOjE1MjY2OTc0NDAsInByaXZhdGVDbGFpbXMiOnsiY29uc2VudFRva2VuIjpudWxsLCJkZXZpY2VJZCI6ImFtem4xLmFzay5kZXZpY2UuQUhTSUNRQUtLTFZZWE5YTjY2SDNSVFFQVUFIR0pQVVFYRzRWQjJEQ1I2R00yQlFWSkZCRVkyWFg3VEZOSDVRWUpTUkJTNTJGM0EyV0hYUTdZWlFGN1paSFNFN0lPSUJWTUxHWFg3V1BZVVU2TTRZQlQ3TUdJS09KV0RWRk41T1k0VUFFT0hHWURNR0hSNFNJUENVQkJVM0xQWTZBIiwidXNlcklkIjoiYW16bjEuYXNrLmFjY291bnQuQUdXVVVBMkZLMjZYQVNEVjZSTFdYWkpOQzRCUTJDQ1hLTUZGSUtBWlJLRE5YMjNFM1dJRVpJT1gySTUyUk1ZQ0pLQkE1QkNBR0pIS0NNVUZKNDJSMllIRFBMSjVJT1c3V1JZRU43UlpONkdTSjZLREE0RlJUUUZBTlNYRldEWFNNM0kzVU1ITkEyTFlFV1lUUk5ETzZCUUdMVE9YTTNaSlFSVkhRS0VHSzRGT05CRkdBTlY1UzdENlNFSVJQUlo0NkZGVUxOV1laTU1XQ1BJIn19.B5QY0DjMHGL9-MLrU5t6whFdcbaZEn7nEdIR3mthXwd-hnG15DFFNaFwMEakey2KawUAsh9LuFKZbKq8Aun4Xf2o_-66hjCRCE0blijEqxKiR-_XYblOapfAF2vKqht3gvJ32JmgRV5K3b46JzYEUIIPuEMDviSHKmFSYWK0YS9Vr2GpGTcbc61Z9zWiHPp3U82oHnxOrYTscpboKwWKH9uCU7uU0rUOgU4qvDDelFfqkV-fko4SFCD9CY3CHlww3aNn82eVDhmNkdHxWhSTE1A5CnQ1Xvy2ukep8DZO5403aEDdCo8I1szRjpovp2yM1nVSBTJz9m7VRI1HR0IQeA"
        }
    },
    "request": {
        "type": "IntentRequest",
        "requestId": "amzn1.echo-api.request.2806fa75-ae32-40c9-a964-6fd2b6038fd6",
        "timestamp": "2018-05-19T02:37:20Z",
        "locale": "en-US",
        "intent": {
            "name": "TrainTimeAway",
            "confirmationStatus": "NONE",
            "slots": {
                "route": {
                    "name": "route",
                    "value": "green E",
                    "resolutions": {
                        "resolutionsPerAuthority": [
                            {
                                "authority": "amzn1.er-authority.echo-sdk.amzn1.ask.skill.489c1bc5-928a-436e-93d1-6edf0d25d6e3.mbta_route",
                                "status": {
                                    "code": "ER_SUCCESS_MATCH"
                                },
                                "values": [
                                    {
                                        "value": {
                                            "name": "Green-E",
                                            "id": "37ed9d45dc23b80a94cdd17e51096c58"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    "confirmationStatus": "NONE"
                },
                "stop": {
                    "name": "stop",
                    "value": "Brigham circle",
                    "resolutions": {
                        "resolutionsPerAuthority": [
                            {
                                "authority": "amzn1.er-authority.echo-sdk.amzn1.ask.skill.489c1bc5-928a-436e-93d1-6edf0d25d6e3.mbta_stop",
                                "status": {
                                    "code": "ER_SUCCESS_MATCH"
                                },
                                "values": [
                                    {
                                        "value": {
                                            "name": "Brigham Circle",
                                            "id": "f7b0ed5d4349618fea747b562276a105"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    "confirmationStatus": "NONE"
                },
                "direction": {
                    "name": "direction",
                    "value": "westbound",
                    "resolutions": {
                        "resolutionsPerAuthority": [
                            {
                                "authority": "amzn1.er-authority.echo-sdk.amzn1.ask.skill.489c1bc5-928a-436e-93d1-6edf0d25d6e3.mbta_direction",
                                "status": {
                                    "code": "ER_SUCCESS_MATCH"
                                },
                                "values": [
                                    {
                                        "value": {
                                            "name": "Westbound",
                                            "id": "393adf693f82ea3a6c178a1852cde819"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    "confirmationStatus": "NONE"
                }
            }
        },
        "dialogState": "STARTED"
    }
}

lambda_handler(testJson, "")
