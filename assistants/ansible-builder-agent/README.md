mkdir <agent_folder>
copy agents to .agents
copy goosehints to .goosehints

Goose folder structure:

~/.config/goose/ 
├── .goosehints          # Global scope agent hints/instructions
├── .agents              
│
├── ansible-builder/    
│   ├── .goosehints      # Project-wide agent hints/instructions
│   ├── .agents
│
└── ansible-tester/
    ├── .goosehints 
    ├── .agents
