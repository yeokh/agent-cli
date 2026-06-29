https://pi.dev/
https://github.com/earendil-works/pi

curl -fsSL https://pi.dev/install.sh | sh

npm list -g --depth=0

export ANTHROPIC_API_KEY=<redacted-anthropic-api-key>
pi
/login


AGENTS.md - project/folder level instructions file.


### TEST CASE 1 ###
Please read the .md file instruction in the ./agent folder.  Then process the files in the ./inbox folder.  And write the results and logs in the ./outbox folder.  Stop once you have process all the files in the inbox.

### TEST CASE 2 ###
I want you to generate some examples of text based charts using Python.  Please use Python environment.  Please download a CSV file of some statistical data such as the Titanic survival rate sample data.  Analyse the CSV data and determine the charts that should be generated to showcase the findings.  Write a Python program to generate and display the text charts on the terminal, using Python libraries such as Asciichartpy, Plotext, and Tplot.  Create this project in ./wrk/textchart folder and add this instruction to a README.md file.




### Build pi container and run in container ###

Edit a Containerfile for pi cli/agent

You can set the API keys environment variables (e.g., ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY)
or add them directly into the agent's configuration file:

$ cat ~/.pi/agent/auth.json

{
  "anthropic": {
    "type": "api_key",
    "key": "<redacted-anthropic-api-key>"
  },
  "openrouter": {
    "type": "api_key",
    "key": "<redacted-openrouter-api-key>"
  }
}

Ref: https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/providers.md#api-keys


### Run test ###

podman build -t pi-agent:latest -f Containerfile
mkdir agent inbox outbox
sudo chown -R 1001:0 outbox

podman run -it --rm -e OPENAI_API_KEY=<redacted-api-key>     \
       -v ./agent:/opt/app-root/src/agent:ro,z   \
       -v ./inbox:/opt/app-root/src/inbox:ro,z   \
       -v ./outbox:/opt/app-root/src/outbox:rw,z \
       localhost/pi-agent:latest

If error with outbox, do chmod 777 outbox or remove the z flag for the outbox.
Or disable SELinux labelling for the container with podman run -it --rm --security-opt label=disable ...


