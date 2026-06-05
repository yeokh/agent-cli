https://github.com/google-antigravity/antigravity-sdk-python
""" Install Antigravity CLI """
# mkdir agy; cd agy
# curl -fsSL https://antigravity.google/cli/install.sh | bash

""" Setup Antigravity SDK ###
# git clone https://github.com/google-antigravity/antigravity-sdk-python
# mkdir wrk; cd wrk
# uv init; uv sync
# source .venv/bin/activate
# uv pip install google-antigravity

# export GEMINI_API_KEY="your_api_key_here"
# export GEMINI_API_KEY="AIzaSyAnYluY87ejfW89SUKERxDIejmCaayHyCk"
# cd anti*; cd ex*; cd gett*
# python hello_world.py

""" If missing module error, could be due to glibc version, should be > 2.35. Use ldd --version to check """
""" RHEL 9 uses 2.34 and RHEL 10 uses 2.39 """

>>> SDK DOES NOT WORK ON RHEL 9
