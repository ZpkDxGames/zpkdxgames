<h1 align="center">⚡ Tonim — Reliable Tools, Playful Ideas</h1>

<p align="center">
  Brazilian Computer Science student and developer building performance-minded Minecraft plugins and practical web applications. I create for server owners, communities, users, and teams that value customization, stability, and thoughtful user experiences.
</p>

<p align="center">
  <a href="https://github.com/ZpkDxGames">
    <img alt="Primary Language: Java" src="https://img.shields.io/badge/Primary%20Language-Java-ED8B00?style=for-the-badge&logo=openjdk&logoColor=white">
  </a>
  <a href="https://papermc.io/">
    <img alt="Framework: Paper API" src="https://img.shields.io/badge/Framework-Paper%20API-222222?style=for-the-badge">
  </a>
  <a href="#-license">
    <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge">
  </a>
  <a href="https://github.com/ZpkDxGames">
    <img alt="Repository Status: Active" src="https://img.shields.io/badge/Status-Actively%20Maintained-38BDF8?style=for-the-badge">
  </a>
</p>

<p align="center">
  <a href="https://ajt-portfolio.vercel.app/">
    <img alt="Portfolio" src="https://img.shields.io/badge/Portfolio-Visit-0F766E?style=flat-square&logo=vercel&logoColor=white">
  </a>
  <a href="https://www.linkedin.com/in/antoniojtneto">
    <img alt="LinkedIn" src="https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat-square&logo=linkedin&logoColor=white">
  </a>
  <a href="mailto:antoniojtneto.corp@gmail.com">
    <img alt="Email" src="https://img.shields.io/badge/Email-Contact-EA4335?style=flat-square&logo=gmail&logoColor=white">
  </a>
  <a href="mailto:antoniojtneto.corp@gmail.com">
    <img alt="Open to Opportunities" src="https://img.shields.io/badge/Open%20to-Opportunities-22C55E?style=flat-square">
  </a>
</p>

---

## 👨‍💻 About Me

I’m **Tonim**, also known online as **ZpkDxGames**. I combine software development with hands-on experience in financial and administrative operations, where organization, accuracy, documentation, and dependable processes are essential.

- **Based in Brazil:** Building projects for both Portuguese- and English-speaking users.
- **Studying Computer Science:** Continuously strengthening my software engineering foundations.
- **Creating practical solutions:** Developing Minecraft plugins, responsive websites, and workflow-focused tools.
- **Prioritizing reliability:** Designing around performance, maintainability, configuration, and real-world usage.
- **Seeking new opportunities:** Open to roles in technology, software development, administration, finance, and related operational areas.

> **My approach:** Build useful tools with precision, curiosity, and a little bit of Minecraft.

## ✨ Key Features

- **Builds extensible Minecraft tooling:** Creates configurable Paper plugins that help server owners manage gameplay systems efficiently.
- **Designs responsive web experiences:** Produces polished, accessible interfaces for desktop and mobile users.
- **Optimizes demanding workflows:** Reduces unnecessary processing through caching, batched persistence, and focused event handling.
- **Integrates established platforms:** Connects projects with MiniMessage, Vault, LuckPerms, PlaceholderAPI, Google Sheets, and external APIs.
- **Improves administrative usability:** Provides clear configuration, informative interfaces, and practical management tools.
- **Documents for maintainability:** Structures projects so developers, contributors, and operators can understand and extend them confidently.

## 🚀 Featured Projects

| Project | Status | Purpose |
| :--- | :---: | :--- |
| [**🎒 PlexonBackpacks**](https://github.com/ZpkDxGames/PlexonBackpacks) | ![Beta](https://img.shields.io/badge/Beta-F59E0B?style=flat-square) | Provides tiered custom-head backpacks with owner binding, inventory safety, and performance-minded persistence. |
| [**🎁 Plexon DailyRewards**](https://github.com/ZpkDxGames/Plexon-DailyRewards) | ![Beta](https://img.shields.io/badge/Beta-F59E0B?style=flat-square) | Delivers group- and world-aware reward tracks, MiniMessage interfaces, administrative tools, and configurable persistence. |
| [**🧱 GhostBlocks**](https://github.com/ZpkDxGames/GhostBlocks) | ![Released](https://img.shields.io/badge/Released-22C55E?style=flat-square) | Enables visible blocks without collision through categorized interfaces and efficient block lookups. |
| [**💬 PlexonChats**](https://github.com/ZpkDxGames/PlexonChats) | ![Released](https://img.shields.io/badge/Released-22C55E?style=flat-square) | Adds local and global chat, private messages, mentions, item sharing, announcements, and MiniMessage formatting. |

- **Current web focus:** Refining my [professional portfolio](https://ajt-portfolio.vercel.app/) and responsive applications built around reliable workflows.
- **Current plugin focus:** Improving scalability, customization, persistence, and administrator-facing tools across the Plexon project family.

## 🧰 Tech Stack

<p align="center">
  <img
    alt="Java, Maven, Git, GitHub, HTML, CSS, JavaScript, Next.js, and Vercel"
    src="https://skillicons.dev/icons?i=java,maven,git,github,html,css,js,nextjs,vercel&perline=9"
  >
</p>

| Category | Technologies | Primary Use |
| :--- | :--- | :--- |
| **Frontend** | HTML, CSS, JavaScript, Next.js | Responsive interfaces, landing pages, portfolios, and web applications |
| **Backend** | Java, Paper/Bukkit APIs, Maven, MiniMessage | Minecraft plugins, business logic, commands, events, and integrations |
| **Database & Persistence** | CSV, YAML, Google Sheets | Configuration, player data, cached records, and dynamic content |
| **DevOps** | Git, GitHub, Vercel | Version control, collaboration, deployment, and release workflows |
| **Integrations** | Vault, LuckPerms, PlaceholderAPI, third-party APIs | Permissions, economy, placeholders, and external services |

## ⚡ Quick Start

The example below demonstrates the typical workflow for exploring and building one of my Maven-based Paper projects. **Always check the selected repository’s README** for its exact Java, Paper, dependency, and configuration requirements.

### Prerequisites

```bash
git --version
java -version
mvn -version
```

### Installation

```bash
git clone "https://github.com/ZpkDxGames/<repository-name>.git"
cd "<repository-name>"

mvn clean package
```

### Running the Project

```bash
# Copy the compiled plugin into your Paper server
cp "target/<plugin-name>-<version>.jar" "<paper-server>/plugins/"

# Start the server using its configured Paper JAR
java -jar "<paper-server>/<paper-server-jar>.jar" --nogui
```

- **Replace `<repository-name>`** with the repository you want to build.
- **Replace `<plugin-name>` and `<version>`** with the generated artifact name.
- **Replace `<paper-server>` and `<paper-server-jar>`** with your local server paths.
- **Review the project documentation** before deploying the plugin to a production server.

## 🧪 Usage Example

The following example builds and installs **PlexonBackpacks**:

```bash
git clone https://github.com/ZpkDxGames/PlexonBackpacks.git
cd PlexonBackpacks

mvn clean package

cp "target/PlexonBackpacks-<version>.jar" "<paper-server>/plugins/"
java -jar "<paper-server>/<paper-server-jar>.jar" --nogui
```

- **Configure the plugin:** Edit the generated files inside `<paper-server>/plugins/PlexonBackpacks/`.
- **Apply changes safely:** Restart the server or follow the plugin-specific reload instructions.
- **Verify the installation:** Review the startup console for enablement messages or dependency warnings.
- **Test before production:** Validate new builds on a separate development server first.

## 📊 GitHub Activity

<p align="center">
  <a href="https://github.com/ZpkDxGames?tab=followers">
    <img alt="GitHub Followers" src="https://img.shields.io/github/followers/ZpkDxGames?style=for-the-badge&logo=github&label=Followers&color=22D3EE">
  </a>
  <a href="https://github.com/ZpkDxGames?tab=repositories">
    <img alt="GitHub Stars" src="https://img.shields.io/github/stars/ZpkDxGames?affiliations=OWNER&style=for-the-badge&logo=github&label=Stars&color=A78BFA">
  </a>
  <img alt="Profile Views" src="https://komarev.com/ghpvc/?username=ZpkDxGames&style=for-the-badge&color=22D3EE&label=PROFILE+VIEWS">
</p>

<p align="center">
  <a href="https://github.com/ZpkDxGames">
    <img
      width="96%"
      alt="ZpkDxGames contribution activity graph"
      src="https://github-readme-activity-graph.vercel.app/graph?username=ZpkDxGames&bg_color=0d1117&color=c9d1d9&line=22d3ee&point=a78bfa&area=true&hide_border=true"
    >
  </a>
</p>

<p align="center">
  <sub>Statistics are generated from public GitHub activity and update automatically.</sub>
</p>

## 🤝 Contributing

Contributions, bug reports, and constructive suggestions are welcome on repositories that accept community changes.

- **Choose a project:** Review its README, open issues, and existing contribution instructions.
- **Discuss significant changes:** Open an issue before implementing a large feature or architectural revision.
- **Create a focused branch:** Keep each branch limited to one fix or feature.
- **Test your changes:** Confirm the project builds successfully and preserves existing behavior.
- **Document the impact:** Explain what changed, why it changed, and how reviewers can verify it.
- **Submit a pull request:** Use a clear title and include screenshots, logs, or reproduction steps when relevant.

```bash
git checkout -b "feat/<short-description>"
git add .
git commit -m "feat: <concise-summary>"
git push origin "feat/<short-description>"
```

## 📄 License

This profile README is available under the **MIT License**. Individual projects may define their own licenses, and each repository’s license takes precedence for its source code and distributed artifacts.

## 📫 Contact

| Channel | Link |
| :--- | :--- |
| **Professional portfolio** | [ajt-portfolio.vercel.app](https://ajt-portfolio.vercel.app/) |
| **Email** | [antoniojtneto.corp@gmail.com](mailto:antoniojtneto.corp@gmail.com) |
| **LinkedIn** | [linkedin.com/in/antoniojtneto](https://www.linkedin.com/in/antoniojtneto) |
| **GitHub** | [github.com/ZpkDxGames](https://github.com/ZpkDxGames) |
| **Modrinth** | [modrinth.com/user/ZpkDxGames](https://modrinth.com/user/ZpkDxGames) |
| **Discord community** | [discord.gg/DC3pFQSJy7](https://discord.gg/DC3pFQSJy7) |
| **WhatsApp** | [Send a message](https://wa.me/5534999953803) |

---

<p align="center">
  <strong>Open to thoughtful collaborations, useful software projects, Minecraft server tooling, and new professional opportunities.</strong>
</p>
