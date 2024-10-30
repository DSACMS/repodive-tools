# repodive-tools
Scripts and tools to gather information about git repositories.

## About the Project
This repository is a collection of scripts and tools for a given repodiving effort. Repodiving in this context means going through 
a git repository and gathering relevant information for a specific purpose. 

<!-- 
### Project Mission
**{project mission}** -->


### Agency Mission
We're a group of civic-minded technologists transforming how the federal government delivers healthcare to the American people.


### Team Mission
Establish and maintain guidance, policies, practices, and talent pipelines that advance equity, build trust, and amplify impact across CMS, HHS, and Federal Open Source Ecosystems by working and sharing openly.

## Core Team

A full list of contributors can be found on [https://github.com/DSACMS/repodive-tools/graphs/contributors](https://github.cms.gov/DSACMS/repodive-tools/graphs/contributors).

<!--
## Documentation Index

TODO: This is a like a 'table of contents" for your documentation. Tier 0/1 projects with simple README.md files without many sections may or may not need this, but it is still extremely helpful to provide "bookmark" or "anchor" links to specific sections of your file to be referenced in tickets, docs, or other communication channels.

**{list of .md at top directory and descriptions}**
-->

<!--
## Repository Structure

TODO: Using the "tree -d" command can be a helpful way to generate this information, but, be sure to update it as the project evolves and changes over time.

**{list directories and descriptions}**
-->

## Development and Software Delivery Lifecycle
We follow GitHub Flow with protected branches and pull request reviews. Development includes automated code analysis, security scanning, and adherence to CMS Open Source Policy guidelines. See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## Local Development
To run locally, please follow the instructions in [CONTRIBUTING.md](CONTRIBUTING.md) under Buidling the Project and Building Dependencies.


## Usage

Run SCC on repos:

    1. Make sure that scc is installed on your machine
    2. Set valid environment variables including GitHub token
    3. `./run-scc-on-repos.sh <Directory to store GitHub code>`

Note: The SCC script will clone the repositories in the directory that you specify. If the 
repository already exists in the directory then it will not download it again. This is useful 
for if you want to re-use this directory to run the other scripts on it. 

Gen Gource logs on repos:

    1. Make sure that gource is installed on your machine
    2. Set valid environment variables including GitHub token
    3. `./gen-gource-logs-on-repos.sh <Directory to store GitHub code`

Note: The gource script will clone the repositories in the directory that you specify. If the 
repository already exists in the directory then it will not download it again. This is useful 
for if you want to re-use this directory to run the other scripts on it. 


Run contributor resolution (rough):

    1. `./run-contrib-resolution.sh <Directory with the GitHub Code already there>`
    3. Enter ctrl+d for any empty records that appear
    4. `./concat.sh`
    5. Look at merged_output.txt and enjoy!


Note: this script assumes that all of the repositories have been cloned already.


<!--
## Coding Style and Linters

TODO - Add the repo's linting and code style guidelines

Each application has its own linting and testing guidelines. Lint and code tests are run on each commit, so linters and tests should be run locally before committing.
-->

<!--
## Branching Model

TODO - with example below:
This project follows [trunk-based development](https://trunkbaseddevelopment.com/), which means:

* Make small changes in [short-lived feature branches](https://trunkbaseddevelopment.com/short-lived-feature-branches/) and merge to `main` frequently.
* Be open to submitting multiple small pull requests for a single ticket (i.e. reference the same ticket across multiple pull requests).
* Treat each change you merge to `main` as immediately deployable to production. Do not merge changes that depend on subsequent changes you plan to make, even if you plan to make those changes shortly.
* Ticket any unfinished or partially finished work.
* Tests should be written for changes introduced, and adhere to the text percentage threshold determined by the project.

This project uses **continuous deployment** using [Github Actions](https://github.com/features/actions) which is configured in the [./github/workflows](.github/workflows) directory.

Pull-requests are merged to `main` and the changes are immediately deployed to the development environment. Releases are created to push changes to production.
-->

<!--
## Contributing
Thank you for considering contributing to an Open Source project of the US Government! For more information about our contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).
-->

<!--
## Codeowners
The contents of this repository are managed by **{responsible organization(s)}**. Those responsible for the code and documentation in this repository can be found in [CODEOWNERS.md](CODEOWNERS.md).
-->

<!--
## Community
The repodive-tools team is taking a community-first and open source approach to the product development of this tool. We believe government software should be made in the open and be built and licensed such that anyone can download the code, run it themselves without paying money to third parties or using proprietary software, and use it as they will.

We know that we can learn from a wide variety of communities, including those who will use or will be impacted by the tool, who are experts in technology, or who have experience with similar technologies deployed in other spaces. We are dedicated to creating forums for continuous conversation and feedback to help shape the design and development of the tool.

We also recognize capacity building as a key part of involving a diverse open source community. We are doing our best to use accessible language, provide technical and process documents, and offer support to community members with a wide variety of backgrounds and skillsets.
-->

<!--
### Community Guidelines
Principles and guidelines for participating in our open source community are can be found in [COMMUNITY_GUIDELINES.md](COMMUNITY_GUIDELINES.md). Please read them before joining or starting a conversation in this repo or one of the channels listed below. All community members and participants are expected to adhere to the community guidelines and code of conduct when participating in community spaces including: code repositories, communication channels and venues, and events.
-->

<!--
## Feedback
If you have ideas for how we can improve or add to our capacity building efforts and methods for welcoming people into our community, please let us know at **{contact email}**. If you would like to comment on the tool itself, please let us know by filing an **issue on our GitHub repository.**
-->

<!--
## Glossary
Information about terminology and acronyms used in this documentation may be found in [GLOSSARY.md](GLOSSARY.md).
-->

## Policies

### Open Source Policy

We adhere to the [CMS Open Source
Policy](https://github.com/CMSGov/cms-open-source-policy). If you have any
questions, just [shoot us an email](mailto:opensource@cms.hhs.gov).

### Security and Responsible Disclosure Policy

*Submit a vulnerability:* Vulnerability reports can be submitted through [Bugcrowd](https://bugcrowd.com/cms-vdp). Reports may be submitted anonymously. If you share contact information, we will acknowledge receipt of your report within 3 business days.

For more information about our Security, Vulnerability, and Responsible Disclosure Policies, see [SECURITY.md](SECURITY.md).

### Software Bill of Materials (SBOM)

A Software Bill of Materials (SBOM) is a formal record containing the details and supply chain relationships of various components used in building software. 

In the spirit of [Executive Order 14028 - Improving the Nation’s Cyber Security](https://www.gsa.gov/technology/it-contract-vehicles-and-purchasing-programs/information-technology-category/it-security/executive-order-14028), a SBOM for this repository is provided here: https://github.com/{{ cookiecutter.project_org }}/{{ cookiecutter.project_repo_name }}/network/dependencies.

For more information and resources about SBOMs, visit: https://www.cisa.gov/sbom.

## Public domain

This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/) as indicated in [LICENSE](LICENSE).

All contributions to this project will be released under the CC0 dedication. By submitting a pull request or issue, you are agreeing to comply with this waiver of copyright interest.