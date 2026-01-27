# Contributing to [Project Name]

Hello! We're glad you're interested in contributing to this project. Currently in early development (prototype stage), both architecture and logic are under rapid iteration. All forms of contributions are welcome, especially if you find any "code smells" - please feel free to suggest improvements!

## 🎯 Key Contribution Areas
We urgently need contributions in the adapter module, focusing on:

**Platform Integration**: Connect with more third-party platforms or APIs.

**x402 Protocol**: Improve protocol parsing, encapsulation, and compatibility implementation.

**Payment Agent System**: Enhance automation decision-making and execution capabilities in payment workflows.

## 🛠 Contribution Process
For better management, please follow these steps:

### 1. Branch Management
- Never commit directly to main branch
- Fork the repository first, then create a feature branch from main with naming convention:
  - `feat/your-feature-name` for new features
  - `refactor/improvement-name` for code improvements

### 2. Testing Requirements
No test, no merge: We rely on tests to maintain functionality during early development.

**For any feature you add:**
- Write corresponding unit/integration tests in `tests/` directory
- Ensure all tests pass locally before submitting PR

### 3. Code Quality Declaration
If you find existing implementations problematic or have better architectural designs:
- Create an Issue for discussion
- Or explain your refactoring rationale in Pull Request
We welcome any improvements that enhance system elegance!

### 4. Submitting Pull Request (PR)
Draft PRs are welcome! Early PRs allow us to discuss implementation strategies.

**In PR description, please clearly state:**
- What problem you solved?
- What platforms/protocols/agent logic you added?
- How to run your test cases?

## 💬 Contact & Feedback
For questions, feel free to leave messages via [GitHub Issues].

---

## 📁 Current Project Structure
```
├── .env.production
├── .env.sandbox
├── .gitignore
├── .python-version
├── pyproject.toml
├── README.md
├── uv.lock
├── assets/
├── docs/
├── scripts/
├── src/
│   └── terrazip/
│       ├── adapters/
│       ├── ai/
│       ├── cores/
│       ├── models/
│       ├── utils/
│       └── x402_mock/
├── tests/
└── README.cn.md