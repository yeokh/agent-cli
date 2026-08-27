https://hermes-agent.nousresearch.com/docs/

# sudo dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
# sudo dnf install -y ripgrep

# curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash


AGENTS.md - project/folder level instructions file.


### TEST CASE 1 ###
please read the .md file instruction in the ./agent folder.  Then process the files in the ./inbox folder.  And write
  the results and logs in the ./outbox folder.  Stop once you have process all the files in the inbox.

### TEST CASE 2 ###
I want you to generate some examples of text based charts using Python.  Please use Python environment.  Please download a CSV file of some statistical data such as the Titanic survival rate sample data.  Analyse the CSV data and determine the charts that should be generated to showcase the findings.  Write a Python program to generate and display the text charts on the terminal, using Python libraries such as Asciichartpy, Plotext, and Tplot.  Create this project in ./wrk/textchart folder and add this instruction to a README.md file.


## A2A Gateway ##

$ hermes gateway setup
$ hermes gateway

$ curl 127.0.0.1:9900/.well-known/agent-card.json
$ curl -N -s -X POST http://127.0.0.1:9900/   -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{ 
    "jsonrpc": "2.0", 
    "id": "req-3",
    "method": "message/stream", 
    "params": { 
      "message": { 
        "role": "user",
        "parts": [{ "kind": "text", "text": "list your skills" }],
        "messageId": "msg-003"
      }
    }
  }' 

