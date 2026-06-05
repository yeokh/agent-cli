https://openrouter.ai/docs/cookbook/coding-agents/codex-cli
https://github.com/openai/codex
npm i -g @openai/codex

Codex uses a config.toml file, typically located at ~/.codex/config.toml. 
Create or edit this file with the following configuration:
>>
model_provider = "openrouter"
model_reasoning_effort = "high"
model="openai/gpt-5.3-codex"
[model_providers.openrouter]
name = "openrouter"
base_url="https://openrouter.ai/api/v1"
env_key="OPENROUTER_API_KEY"

>>
export OPENROUTER_API_KEY="sk-or-..."

>>
cd /path/to/your/project
codex


### TEST CASE 1 ###
please read the .md file instruction in the ./agent folder.  Then process the files in the ./inbox folder.  And write
  the results and logs in the ./outbox folder.  Stop once you have process all the files in the inbox.

### TEST CASE 2 ###
I want you to generate some examples of text based charts using Python.  Please use Python environment.  Please download a CSV file of some statistical data such as the Titanic survival rate sample data.  Analyse the CSV data and determine the charts that should be generated to showcase the findings.  Write a Python program to generate and display the text charts on the terminal, using Python libraries such as Asciichartpy, Plotext, and Tplot.  Create this project in ./wrk/textchart folder and add this instruction to a README.md file.
