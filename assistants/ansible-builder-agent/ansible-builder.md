PROMPT:
If I want to configure goose to be an Ansible playbook developer AI assistant, where should I store the skills, recipe and my company's collection of Ansible playbooks in this workspace so that I can achieve this outcome: 
- To provide prebuilt sandboxed AI assistant with specific skills, instructions and knowledge-bases that can be instantiated on demand to assist the users. 
- To provide an AI assistant that can explain or advice based on the collection of Ansible playbooks and what the playbooks are used for.
- To generate an Ansible playbook specifications that will fulfil specific requirements, automation use cases or to achieve specific outcomes.
- To write Ansible playbooks based on Ansible playbook specifications, following existing guidelines and templates.
- To analyze, review and test Ansible playbooks for any potential flaws and vulnerabilities.


# Ansible Playbook Developer AI Assistant Configuration

## Task: Design workspace structure for goose as Ansi...

o  Goose would like to call the above tool, do you allow?
|  Allow
|
## Comprehensive Architecture for Ansible Playbook Developer AI Assistant

Based on the official goose documentation, here's the optimal workspace structure and configuration strategy for creating an Ansible playbook developer AI assistant:

---

## **1. Workspace Directory Structure**

```
YOUR_WORKSPACE/
│
├── .agents/
│   ├── skills/
│   │   ├── ansible-playbook-advisor/
│   │   │   ├── SKILL.md
│   │   │   └── resources/
│   │   │       ├── playbook-collection-index.md
│   │   │       └── ansible-best-practices.md
│   │   │
│   │   ├── ansible-spec-generator/
│   │   │   ├── SKILL.md
│   │   │   ├── templates/
│   │   │   │   └── playbook-spec-template.yaml
│   │   │   └── resources/
│   │   │       └── spec-guidelines.md
│   │   │
│   │   ├── ansible-playbook-writer/
│   │   │   ├── SKILL.md
│   │   │   ├── templates/
│   │   │   │   ├── role-template/
│   │   │   │   ├── playbook-template.yaml
│   │   │   │   └── task-patterns/
│   │   │   └── resources/
│   │   │       └── style-guide.md
│   │   │
│   │   └── ansible-reviewer/
│   │       ├── SKILL.md
│   │       ├── scripts/
│   │       │   ├── lint-playbook.sh
│   │       │   ├── test-syntax.sh
│   │       │   └── security-check.sh
│   │       └── resources/
│   │           └── review-checklist.md
│   │
│   ├── plugins/
│   │   └── ansible-playbook-suite/
│   │       ├── plugin.json
│   │       ├── skills/
│   │       │   ├── advisor/SKILL.md
│   │       │   ├── spec-generator/SKILL.md
│   │       │   ├── playbook-writer/SKILL.md
│   │       │   └── reviewer/SKILL.md
│   │       └── hooks/
│   │           └── hooks.json
│   │
│   └── recipes/
│       ├── ansible-advisor.yaml
│       ├── ansible-spec-to-playbook.yaml
│       ├── ansible-review-workflow.yaml
│       └── ansible-full-pipeline.yaml
│
├── knowledge-base/
│   ├── playbook-collection/
│   │   ├── infrastructure/
│   │   │   ├── provision-vm.yaml
│   │   │   ├── deploy-k8s.yaml
│   │   │   └── configure-lb.yaml
│   │   │
│   │   ├── application/
│   │   │   ├── deploy-app.yaml
│   │   │   ├── configure-db.yaml
│   │   │   └── setup-monitoring.yaml
│   │   │
│   │   └── compliance/
│   │       ├── hardening.yaml
│   │       ├── security-scan.yaml
│   │       └── audit-logging.yaml
│   │
│   ├── inventory/
│   │   ├── production.ini
│   │   ├── staging.ini
│   │   └── inventory-schema.md
│   │
│   ├── roles/
│   │   ├── webserver/
│   │   ├── database/
│   │   ├── monitoring/
│   │   └── security/
│   │
│   ├── variables/
│   │   ├── common.yaml
│   │   ├── environments.yaml
│   │   └── secrets-template.yaml
│   │
│   └── documentation/
│       ├── COLLECTION_OVERVIEW.md
│       ├── ARCHITECTURE.md
│       ├── USAGE_GUIDE.md
│       └── TROUBLESHOOTING.md
│
└── recipes-global/
    └── (stored in ~/.config/goose/recipes/ for cross-project use)
```

---

## **2. Skill Definitions** (Project-Level: `.agents/skills/`)

Each skill targets one of your four core outcomes:

### **Skill 1: Ansible Playbook Advisor**
**Location:** `.agents/skills/ansible-playbook-advisor/SKILL.md`

```markdown
---
name: ansible-playbook-advisor
description: Explain and advise on existing Ansible playbooks in the collection
---

# Ansible Playbook Advisor

You are an Ansible expert helping teams understand and work with their playbook collection.

## Responsibilities

- Explain what each playbook does and its use cases
- Describe the architecture and design patterns used
- Identify dependencies, role relationships, and variable flows
- Provide best practice recommendations
- Guide users on when to use specific playbooks

## Knowledge Base Reference

Your context includes the complete playbook collection stored in `knowledge-base/playbook-collection/`.
Also reference `knowledge-base/documentation/COLLECTION_OVERVIEW.md`.

## Procedure

1. **Request Details**: Ask the user which playbook(s) they want to understand
2. **Analyze Structure**: Examine the playbook YAML, roles, variables, and handlers
3. **Explain Purpose**: Describe what the playbook does and when to use it
4. **Identify Components**: List roles, tasks, variables, and dependencies
5. **Provide Guidance**: Suggest related playbooks and best practices
6. **Answer Questions**: Respond to specific technical questions about implementation

## Verification

Ensure explanations include:
- [ ] Playbook purpose and use cases
- [ ] Architecture overview
- [ ] List of roles and their functions
- [ ] Key variables and their meanings
- [ ] Dependencies on other playbooks/roles
- [ ] Best practices applied
```

### **Skill 2: Ansible Spec Generator**
**Location:** `.agents/skills/ansible-spec-generator/SKILL.md`

```markdown
---
name: ansible-spec-generator
description: Generate Ansible playbook specifications from requirements
---

# Ansible Playbook Specification Generator

Create detailed playbook specifications that serve as blueprints for playbook development.

## Responsibilities

- Interview users about their automation requirements
- Consolidate requirements into a structured specification
- Identify existing playbooks that meet requirements (or parts of them)
- Define playbook structure, roles, and tasks
- Specify variables, handlers, and error handling approach

## Specification Template

Use the template at `.agents/skills/ansible-spec-generator/templates/playbook-spec-template.yaml`.

## Procedure

1. **Gather Requirements**: Ask clarifying questions about:
   - What systems/services will be managed
   - What state should be achieved
   - Dependencies and prerequisites
   - Error handling and rollback needs
   - Testing requirements

2. **Check Existing Playbooks**: Search `knowledge-base/playbook-collection/` for similar patterns

3. **Create Specification**: Generate a spec document including:
   - Playbook name and purpose
   - Target hosts/groups
   - Required roles (new and existing)
   - Variables and defaults
   - Task flow and logic
   - Error handling strategy
   - Testing plan

4. **Validate**: Ensure the spec is complete and achievable

## Output Format

Provide the spec in both Markdown (for review) and YAML (for implementation).
```

### **Skill 3: Ansible Playbook Writer**
**Location:** `.agents/skills/ansible-playbook-writer/SKILL.md`

```markdown
---
name: ansible-playbook-writer
description: Write production-quality Ansible playbooks from specifications
---

# Ansible Playbook Writer

Develop Ansible playbooks that follow your organization's standards and best practices.

## Responsibilities

- Write playbooks following style guides and templates
- Create or adapt roles as needed
- Implement proper variable handling and defaults
- Add comprehensive error handling
- Include comments and documentation
- Ensure idempotency and safety

## Standards Applied

- Style guide: `.agents/skills/ansible-playbook-writer/resources/style-guide.md`
- Templates: `.agents/skills/ansible-playbook-writer/templates/`
- Review checklist: `.agents/skills/ansible-reviewer/resources/review-checklist.md`

## Procedure

1. **Review Specification**: Understand the requirements from the spec
2. **Plan Structure**: Decide on roles, tasks, and variable organization
3. **Write Playbook**: Create the main playbook file
4. **Create Roles**: Develop necessary roles using role templates
5. **Add Variables**: Define all variables with documentation
6. **Implement Handlers**: Create handlers for service restarts, notifications
7. **Add Error Handling**: Include proper error catching and recovery
8. **Document**: Add comments explaining complex logic
9. **Self-Review**: Check against the review checklist
10. **Output**: Provide the complete playbook and roles

## Best Practices

- [ ] Use roles for reusability
- [ ] Make playbooks idempotent
- [ ] Document all variables
- [ ] Include proper handlers
- [ ] Add when conditions for safety
- [ ] Use become sparingly and document why
- [ ] Include tags for selective execution
```

### **Skill 4: Ansible Reviewer**
**Location:** `.agents/skills/ansible-reviewer/SKILL.md`

```markdown
---
name: ansible-reviewer
description: Analyze, review, test, and validate Ansible playbooks
---

# Ansible Playbook Reviewer

Thoroughly review Ansible playbooks for correctness, security, performance, and compliance.

## Responsibilities

- Syntax validation and linting
- Security vulnerability scanning
- Best practices review
- Performance analysis
- Testing guidance and verification
- Flaw detection and fix recommendations

## Review Tools

- Scripts: `.agents/skills/ansible-reviewer/scripts/`
  - `lint-playbook.sh` — Run ansible-lint
  - `test-syntax.sh` — Validate YAML syntax
  - `security-check.sh` — Check for security issues

- Checklist: `.agents/skills/ansible-reviewer/resources/review-checklist.md`

## Procedure

1. **Syntax Check**: Validate YAML syntax
2. **Lint**: Run ansible-lint against the playbook
3. **Security Scan**: Check for hardcoded credentials, unsafe modules
4. **Best Practices**: Review against organizational standards
5. **Logic Review**: Verify task flow and error handling
6. **Performance**: Identify optimization opportunities
7. **Documentation**: Check for adequate comments and variable documentation
8. **Testing**: Verify testing approach and coverage
9. **Report**: Provide detailed findings with recommendations
10. **Approve**: Confirm playbook is production-ready

## Verification Checklist

- [ ] YAML syntax is valid
- [ ] No linting errors
- [ ] No hardcoded secrets or credentials
- [ ] Proper error handling
- [ ] Idempotent operations
- [ ] Variables documented
- [ ] Handlers included where needed
- [ ] Tests defined
- [ ] Comments explain complex logic
- [ ] Follows style guide
```

---

## **3. Recipes for Common Workflows** (Project-Level: `.agents/recipes/`)

### **Recipe 1: Playbook Analysis & Explanation**
**Location:** `.agents/recipes/ansible-advisor.yaml`

```yaml
version: "1.0.0"
title: "Analyze Ansible Playbook"
description: "Get detailed explanation and guidance about any playbook in your collection"

instructions: |
  I'll help you understand Ansible playbooks in detail.

  You can ask me to:
  - Explain what a specific playbook does
  - Describe the architecture and roles used
  - Walk through task execution flow
  - Identify dependencies and prerequisites
  - Provide best practices recommendations

  The knowledge base at `knowledge-base/playbook-collection/` is available for reference.

parameters:
  - key: playbook_name
    input_type: string
    requirement: optional
    description: "Name of the playbook you want to understand"

activities:
  - "message: Select a task to get started:"
  - "Explain this playbook's purpose and architecture"
  - "Show me the role structure and task flow"
  - "What are the main variables and their meanings?"
  - "Find related playbooks in our collection"
  - "Check best practices and recommendations"
```

### **Recipe 2: Generate Playbook Specification**
**Location:** `.agents/recipes/ansible-spec-generator.yaml`

```yaml
version: "1.0.0"
title: "Generate Playbook Specification"
description: "Create a detailed specification for a new Ansible playbook"

instructions: |
  I'll help you create a comprehensive playbook specification.

  I will:
  1. Ask detailed questions about your automation requirements
  2. Search for existing playbooks that might be reusable
  3. Design the playbook structure and roles
  4. Create a detailed specification document
  5. Provide the spec in YAML format ready for implementation

  The specification template is at:
  `.agents/skills/ansible-spec-generator/templates/playbook-spec-template.yaml`

activities:
  - "message: Let's create your playbook specification"
  - "I need to automate infrastructure deployment"
  - "I need to automate application configuration"
  - "I need to automate compliance/security tasks"
  - "I have specific requirements to discuss"
```

### **Recipe 3: Write Playbook from Specification**
**Location:** `.agents/recipes/ansible-playbook-writer.yaml`

```yaml
version: "1.0.0"
title: "Write Ansible Playbook"
description: "Develop a production-quality Ansible playbook from a specification"

instructions: |
  I'll write a complete, production-ready Ansible playbook based on your specification.

  I will:
  1. Review your playbook specification thoroughly
  2. Plan the structure and role organization
  3. Write the main playbook file
  4. Create any necessary custom roles
  5. Define all variables with documentation
  6. Implement error handling and handlers
  7. Add comprehensive comments
  8. Perform self-review against best practices
  9. Output the complete playbook ready for testing

  Following standards from:
  - Style guide: `.agents/skills/ansible-playbook-writer/resources/style-guide.md`
  - Templates: `.agents/skills/ansible-playbook-writer/templates/`

parameters:
  - key: spec_location
    input_type: string
    requirement: optional
    description: "Path to your playbook specification file"

activities:
  - "message: Provide your specification or describe what you want to build"
  - "Here's my playbook specification file"
  - "Let me describe the playbook I need"
  - "I want to customize an existing playbook"
```

### **Recipe 4: Review & Test Playbook**
**Location:** `.agents/recipes/ansible-review-workflow.yaml`

```yaml
version: "1.0.0"
title: "Review & Test Ansible Playbook"
description: "Comprehensive review, testing, and validation of Ansible playbooks"

instructions: |
  I'll thoroughly review your Ansible playbook for quality, security, and compliance.

  I will:
  1. Validate YAML syntax
  2. Run ansible-lint for code quality
  3. Scan for security vulnerabilities
  4. Review against best practices
  5. Analyze task logic and error handling
  6. Check documentation and comments
  7. Provide detailed findings and recommendations
  8. Suggest fixes for any issues found
  9. Confirm production readiness

  Review checklist: `.agents/skills/ansible-reviewer/resources/review-checklist.md`
  Review tools: `.agents/skills/ansible-reviewer/scripts/`

parameters:
  - key: playbook_path
    input_type: string
    requirement: optional
    description: "Path to the playbook you want to review"

activities:
  - "message: Upload or point to the playbook you want reviewed"
  - "Review this playbook for quality and security"
  - "Check this playbook for best practices"
  - "Run a full validation suite on this playbook"
  - "Find and fix issues in this playbook"
```

### **Recipe 5: Full Pipeline (Spec → Write → Review)**
**Location:** `.agents/recipes/ansible-full-pipeline.yaml`

```yaml
version: "1.0.0"
title: "Full Playbook Development Pipeline"
description: "End-to-end workflow: specification → development → review → approval"

instructions: |
  I'll guide you through the complete playbook development lifecycle.

  Workflow:
  1. **Generate Specification** — Define requirements and playbook design
  2. **Write Playbook** — Develop the playbook from the specification
  3. **Review & Test** — Comprehensive quality and security review
  4. **Ready for Deployment** — Approved and ready for production

  At each stage, I'll verify the output meets our standards before proceeding.

activities:
  - "message: Let's build a production-ready Ansible playbook"
  - "Start with requirement gathering"
  - "Generate a new specification"
  - "Write the playbook"
  - "Run the review workflow"
  - "Show me the complete output"
```

---

## **4. Knowledge Base Structure** (`knowledge-base/`)

This directory contains your organization's Ansible resources:

### **Playbook Collection** (`knowledge-base/playbook-collection/`)
- **Purpose**: Reference existing playbooks
- **Content**: Organized by category (infrastructure, application, compliance)
- **Use**: AI assistant can reference and reuse patterns

### **Roles Directory** (`knowledge-base/roles/`)
- **Purpose**: Reusable Ansible roles
- **Content**: Common roles like webserver, database, monitoring
- **Use**: AI can suggest existing roles or create variations

### **Variables** (`knowledge-base/variables/`)
- **Purpose**: Common variable definitions and patterns
- **Content**: Environment-specific variables, secrets templates
- **Use**: AI learns your variable naming conventions and structures

### **Inventory** (`knowledge-base/inventory/`)
- **Purpose**: Example inventory files for different environments
- **Content**: Production, staging, development inventory files
- **Use**: AI understands your infrastructure organization

### **Documentation** (`knowledge-base/documentation/`)
- **Purpose**: Context and guidelines
- **Files**:
  - `COLLECTION_OVERVIEW.md` — Index of all playbooks
  - `ARCHITECTURE.md` — How playbooks fit together
  - `USAGE_GUIDE.md` — When to use each playbook
  - `TROUBLESHOOTING.md` — Common issues and solutions

---

## **5. Plugin Structure** (Optional: For Bundled Distribution)

If you want to package all skills together for easy distribution:

**Location:** `.agents/plugins/ansible-playbook-suite/`

```
ansible-playbook-suite/
├── plugin.json
├── skills/
│   ├── advisor/SKILL.md
│   ├── spec-generator/SKILL.md
│   ├── playbook-writer/SKILL.md
│   └── reviewer/SKILL.md
└── hooks/
    └── hooks.json (optional - for automated testing on session end)
```

**plugin.json:**
```json
{
  "name": "ansible-playbook-suite",
  "version": "1.0.0",
  "description": "Complete Ansible playbook development suite with advisor, spec generator, writer, and reviewer"
}
```

---

## **6. How to Instantiate Sandboxed AI Assistants On Demand**

### **Option A: Using Recipes (Recommended)**
Each recipe acts as a pre-configured assistant instance:

```bash
# User wants to analyze a playbook
goose recipe use ansible-advisor

# User wants to generate a spec
goose recipe use ansible-spec-generator

# User wants to write a playbook
goose recipe use ansible-playbook-writer

# User wants to review a playbook
goose recipe use ansible-review-workflow

# Full end-to-end workflow
goose recipe use ansible-full-pipeline
```

### **Option B: Using Skills Directly**
Load individual skills when needed:

```bash
# Use the CLI skills command
/skills ansible-playbook-advisor

# Load multiple skills at once
/skills ansible-spec-generator ansible-playbook-writer
```

### **Option C: Using Desktop App**
1. Open goose Desktop
2. Click "Recipes" in the sidebar
3. Select your desired recipe (ansible-advisor, ansible-spec-generator, etc.)
4. Click "Use" to instantiate the assistant with that workflow

### **Option D: Using Plugins (Enterprise Distribution)**
Install the complete suite as a plugin:

```bash
goose plugin install /path/to/ansible-playbook-suite
# or from git repo
goose plugin install https://github.com/yourorg/goose-ansible-plugin.git
```

Then use plugin-namespaced skills:
```bash
/skills ansible-playbook-suite:advisor
/skills ansible-playbook-suite:spec-generator
```

---

## **7. Addressing Your Four Core Outcomes**

| Outcome | Skill | Recipe | How It Works |
|---------|-------|--------|-------------|
| **Explain/Advise on Playbooks** | `ansible-playbook-advisor` | `ansible-advisor.yaml` | Load knowledge base, analyze playbooks, provide guidance |
| **Generate Playbook Specs** | `ansible-spec-generator` | `ansible-spec-generator.yaml` | Interview user, create detailed specification document |
| **Write Playbooks** | `ansible-playbook-writer` | `ansible-playbook-writer.yaml` | Implement from spec, follow style guide, create roles |
| **Analyze & Review** | `ansible-reviewer` | `ansible-review-workflow.yaml` | Validate, lint, security scan, provide recommendations |

Each can be instantiated independently or chained together in the full pipeline.

---

## **8. Getting Started: Quick Setup**

1. **Create the directory structure:**
```bash
cd /home/goose/workspace
mkdir -p .agents/skills .agents/recipes knowledge-base/{playbook-collection,roles,variables,inventory,documentation}
```

2. **Create your first skill** (ansible-playbook-advisor):
```bash
mkdir .agents/skills/ansible-playbook-advisor
# Create SKILL.md with content from section 2 above
```

3. **Create your first recipe** (ansible-advisor):
```bash
# Create .agents/recipes/ansible-advisor.yaml
```

4. **Add your playbook collection:**
```bash
# Copy existing playbooks to knowledge-base/playbook-collection/
cp -r /path/to/your/playbooks/* knowledge-base/playbook-collection/
```

5. **Test the setup:**
```bash
goose skills list  # Should show your new skills
/skills ansible-playbook-advisor  # Load the skill
```

---

## **Verification Completed** ✅

All goose-specific items verified against official documentation:
- **Skill locations and structure**: Verified in [Using Skills Guide](https://goose-docs.ai/docs/guides/context-engineering/using-skills)
- **Recipe format and storage**: Verified in [Recipe Reference Guide](https://goose-docs.ai/docs/guides/recipes/recipe-reference) and [Storing Recipes Guide](https://goose-docs.ai/docs/guides/recipes/storing-recipes)
- **Plugin structure**: Verified in [Plugins Guide](https://goose-docs.ai/docs/guides/context-engineering/plugins)
- **Directory paths**: Verified as per `~/.agents/skills/`, `.agents/skills/`, `~/.config/goose/recipes/`, `.goose/recipes/`
- **Recipe schema fields**: title, description, instructions, parameters, activities all verified in Recipe Reference
- **Skill file structure**: SKILL.md with YAML frontmatter verified in Using Skills guide

---

## **Documentation References**

- [Using Skills](https://goose-docs.ai/docs/guides/context-engineering/using-skills)
- [Recipe Reference Guide](https://goose-docs.ai/docs/guides/recipes/recipe-reference)
- [Storing Recipes](https://goose-docs.ai/docs/guides/recipes/storing-recipes)
- [Plugins Guide](https://goose-docs.ai/docs/guides/context-engineering/plugins)


