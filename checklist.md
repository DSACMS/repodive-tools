# DSAC OSPO Outbound Review Checklist
## Tier 1: One-Time Release

### Instructions

This is a review process to approve CMS-developed software to be released open source. If you would like your repository to be released, please complete the following steps.

[Instructions](#instructions)

[State the Benefits of Open Sourcing the Project](#state-the-benefits-of-open-sourcing-the-project)

[State the Risks of Open Sourcing the Project](#state-the-risks-of-open-sourcing-the-project)

[Questions](#questions)

[Code Review](#code-review)

[Code Analysis](#code-analysis)

[Review Licensing](#review-licensing)

[Review Commit History](#review-commit-history)

[Review Repository Hygiene](#review-repository-hygiene)

[Review Repository Details](#review-repository-details)

[Additional Notes & Questions](#additional-notes--questions)

[Sign off on risk acceptance of open-sourcing the software product](#sign-off-on-risk-acceptance-of-open-sourcing-the-software-product)

[Flipping the Switch: Making the Repository Public](#flipping-the-switch-making-the-repository-public)

### State the Benefits of Open Sourcing the Project

- [ ] **Cost Savings** 
by making the project freely available, this reduces licensing and acquisition costs.
- [x] **Ease of Repurposing**
The open nature of the code allows users to modify and adapt the software to suit their specific needs, fostering customization and flexibility.
- [ ] **Minimization of Vendor Lock-in/Flexibility of Vendor Choice**
Users are not tied to a single vendor, providing the freedom to choose between different vendors.
- [x] **Enable Transparency**
The source code is accessible and visible to anyone, promoting transparency in how the software functions, which helps build trust.
- [x] **Enable Extension/Extensibility**
Users can extend and enhance the functionality of the software by adding their own features.
- [x] **Increase Interoperability**
Planning in the open enables future compatibility and interoperability between different systems and software applications.
- [x] **Facilitate Experimentation/Early Adoption**
Working in the open encourages experimentation and early adoption of cutting-edge technologies,leading to faster innovation and improvemnet in software capabilities.

### State the Risks of Open Sourcing the Project

- [x] **Security Risks**
Vulnerabilities may be exposed if the code is not thoroughly reviewed, potentially leading to security breaches or exploitation.(See: [Security.md](https://github.com/DSACMS/repo-scaffolder/blob/main/SECURITY.md))Does this project connect to any CMS-internal only systems? Does this project require authorization or authentication to operate? Does this project detail any non-public directories of CMS/HHS systems or people?
- [ ] **Financial Risks**
Costs may arise from maintaining code, community engagemnet, addressing security concerns, or subscription costs, hardware costs, specialized tooling or infrastructure costs, among others. Does this project require any ongoing financial costs or subscription fees?
(e.g. - Cloud Hosting, Specialized build systems, paid maintainers, paid libraries or dependencies.)
- [x] **Privacy Risks**
Does this project require access to non-public, non synthetic PII, PHI, or other internal-only CMS Systems containing such data or information?

---

### Questions

- Does the code contain or touch any private information such as Personal Identifiable Information (PII) or Protected Health Information (PHI)?
  - Can it be removed? Is it absolutely needed to function? Can it be shipped with synthetic data instead?
 - Does the code interface with any CMS' internal-only systems(e.g. mainframes, JIRA instances, databases, etc...)?
 - Does the repository contain any keys or credentials to access or authenticate with CMS' systems?
   - Can it be removed or is it needed?

   If you answered "yes" to any of the above questions, your project may be 'sensitive' in nature, and requires a more thorough review before sharing publicly. Please reach out to opensource@cms.hhs.gov for guidance. If you answer yes to any of these questions above, it is best to seek quidance **before** releasing open source.

 **Results** 
 *The repo currently does not contain any private information and it has been removed from the project.
 The repo does not interface with any CMS internal-only systems.
 The repo does not contain any keys or credentials to access or authenticate with CMS' systems.
 The user must manually enter their Github Key is order to be authenticated*




   




### Code Review

The existing codebase should be given a one time, top-to-bottom code quality and security vulnerability review by two (or more) engineers who have written production code within the past two years, in the languages used in the project Engineers should review credential management practices with the development team to ensure that any keys, passwords, or other sensitive configurations are not checked into source code or in the git history.

The engineers can be federal government employees or trusted partners from outside the agency from other contracts, or from independent testing contracts. Their names, organizations, comments and approval/disapproval on the overall codebase should be tracked in this document.

To provide independent review, ideally the engineers should not have been involved in the development of the software product. This includes engineers who wrote part of the software or who directly provided technical direction and oversight in the creation of the software.

As part of the code review, engineers should reference modern listings of the most significant software security vulnerabilities. For instance, an acceptable description would be that the engineers showed how they used automated tools and manual review to check each item in __OWASP's current 10 Most Critical Web Application Security Risks.__




   **Results**

   *Each file was maticulosly read in order to check for any vulnerablities and general quality. The following is a list of changes that should be made to increase security and quality.*

   - The scripts (gen-gource-logs-on-repos.sh and run-scc-on-repos.sh) contain hardcoded empty TOKEN variables. These should be moved to environment variables or a different secure system
   - There is minimal error handling within the script files (concat.sh and run-contrib-resolution-rough.sh) pertaining to file system operations
   - There is minimal error handling within the API cals made to the GitHub API


   


### Code Analysis 

A best practice and a requirement for releasing a repository open source at many parts of CMS is to run at least one automated tool for code analysis (such as static code analysis, repolinters, secret scanners) on the codebase to detect for security vulnerabilities or sensitive information, and results have been appropriately addressed. Even if all findings are eventually fixed, if the initial scans revealed significant, severe vulnerabilities(such as SQL injection vulnerabilities), this may indicate that the software development team was not adhering to the best practices required for open source public release, and should be given additional review.

Ideally, automated tooling for code analysis should be incorporated as a regularly scheduled part of the software development lifecycle. The development team should briefly document how frequently they commit to running these automated scanning tools, and how they will be running these tests, and who will be monitoring, interpreting, and acting upon the results.


#### Toolkit
   Below is a list of suggested tools to run for code analysis:

| **Tool** |  **Description** |  **Link**   |
:-------| :-------------: | :------: |
| Repo Linter  | Lint repositories for common issues such as missing files etc.| https://github.com/todogroup/repolinter |
|  gitleaks  | Protect and discover secrets using Gitleaks :key:  |  https://github.com/gitleaks/gitleaks
| git filter-repo |  Entirely remove unwanted files / files with sensitive data from a repository's history   |  https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository


**Results**

*Each file was maticulosly analyzed and ran through each of the suggested tools above. Below is the results from running these tools and general analysis*

- Repolinter was run and results are listed below
- Gitleaks was ran and no secrets were found within the git history or repo
- Git filter-repo was not needed to run 



### Review Licensing

Ensure that acceptable licensing is indicated for the project. Most often, software released as open source by the federal government is done so under the Creative Commons Zero 1.0 license.

Suggested licensing:

   **Public Domain**
   
  - This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the CC0 1.0 Universal public domain dedication.

  - All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.

If your project is not being dedicated to the public domain under CC0, due to being work for hire, or some other documented reason, then choosing another [OSI approved license](https://opensource.org/license) is the next best thing.

**Results**

*The CC0 1.0 Universal License is included within the repo.*



### Review Commit History 

Review the history of commits to the version control system used, and whether the team prefers to clean (e.g.,rebase) this history before releasing to the public.

If not rebasing, verify that:

1. There are no obscene or impolite remarks in comments or commit history

2. There are no sensitive internal URLs/IP addresses in comments or commit history 

3. There are no credential files such as passwords, API/SSH/GPG keys checked into the repo

Consider using the following tools to perform the tasks above:

[^1]: Table needs work - [x] 

| Tool        | Description                                                      | Link                                    |
|-------------|------------------------------------------------------------------|-----------------------------------------|
| gitleaks | Open source tool that detects and prevents secrets (passwords/api/ssh keys) checked-in to your git repo | https://github.com/gitleaks/gitleaks   https://akachandwani.medium.com/what-is-gitleaks-and-how-to-use-it-a05f2fb5b034 |
| git filter-repo    | Entirely remove unwanted files / files with sensitive data from a repository's history                     |    https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository                   |

**Results**

*Commit history was checked and is all clear and the automated tools were run*

- Gitleaks was ran and no secrets were found within the git history or repo
- Git filter-repo was not needed to run 


### Review Repository Hygiene

As part of our repository hygiene requirements, the project must include certain files and sections. Using repolinter will help identify missing files and content that will need to be added to your repository before outbounding.

**Running repolinter on your repository**

[^1]: the repolinter.json seems like some sort of link to something



1. Add [repolinter.json](https://github.com/DSACMS/repo-scaffolder/blob/main/tier1/%7B%7Bcookiecutter.project_slug%7D%7D/repolinter.json) to the root directory of your project

[^1]: that command is highlighted green could also think to something? - [x]

2. Run command 
```
repolinter lint .
```
3. The result produces a list of files section existence checks, indicating whether each requirement was met or not.

# Repolinter Report

*This report was generated automatically by the Repolinter.*

This Repolinter run generated the following results:
| ❗  Error | ❌  Fail | ⚠️  Warn | ✅  Pass | Ignored | Total |
|---|---|---|---|---|---|
| 0 | 2 | 2 | 36 | 23 | 63 |

- [DSAC OSPO Outbound Review Checklist](#dsac-ospo-outbound-review-checklist)
  - [Tier 1: One-Time Release](#tier-1-one-time-release)
    - [Instructions](#instructions)
    - [State the Benefits of Open Sourcing the Project](#state-the-benefits-of-open-sourcing-the-project)
    - [State the Risks of Open Sourcing the Project](#state-the-risks-of-open-sourcing-the-project)
    - [Questions](#questions)
    - [Code Review](#code-review)
    - [Code Analysis](#code-analysis)
      - [Toolkit](#toolkit)
    - [Review Licensing](#review-licensing)
    - [Review Commit History](#review-commit-history)
    - [Review Repository Hygiene](#review-repository-hygiene)
- [Repolinter Report](#repolinter-report)
  - [Fail #](#fail-)
    - [❌ `contributing-contains-building-dependencies` #](#-contributing-contains-building-dependencies-)
    - [❌ `contributing-contains-building-the-project` #](#-contributing-contains-building-the-project-)
  - [Warning #](#warning-)
    - [⚠️ `readme-contains-development-and-software-delivery-lifecycle` #](#️-readme-contains-development-and-software-delivery-lifecycle-)
    - [⚠️ `readme-contains-local-development` #](#️-readme-contains-local-development-)
  - [Passed #](#passed-)
    - [✅ `license-file-exists` #](#-license-file-exists-)
    - [✅ `security-file-exists` #](#-security-file-exists-)
    - [✅ `readme-file-exists` #](#-readme-file-exists-)
    - [✅ `contributing-file-exists` #](#-contributing-file-exists-)
    - [✅ `license-contains-license` #](#-license-contains-license-)
    - [✅ `security-contains-security-and-responsible-disclosure-policy` #](#-security-contains-security-and-responsible-disclosure-policy-)
    - [✅ `readme-contains-about-the-project` #](#-readme-contains-about-the-project-)
    - [✅ `readme-contains-project-mission` #](#-readme-contains-project-mission-)
    - [✅ `readme-contains-agency-mission` #](#-readme-contains-agency-mission-)
    - [✅ `readme-contains-team-mission` #](#-readme-contains-team-mission-)
    - [✅ `readme-contains-core-team` #](#-readme-contains-core-team-)
    - [✅ `readme-contains-documentation-index` #](#-readme-contains-documentation-index-)
    - [✅ `readme-contains-repository-structure` #](#-readme-contains-repository-structure-)
    - [✅ `readme-contains-coding-style-and-linters` #](#-readme-contains-coding-style-and-linters-)
    - [✅ `readme-contains-branching-model` #](#-readme-contains-branching-model-)
    - [✅ `readme-contains-contributing` #](#-readme-contains-contributing-)
    - [✅ `readme-contains-codeowners` #](#-readme-contains-codeowners-)
    - [✅ `readme-contains-community` #](#-readme-contains-community-)
    - [✅ `readme-contains-community-guidelines` #](#-readme-contains-community-guidelines-)
    - [✅ `readme-contains-feedback` #](#-readme-contains-feedback-)
    - [✅ `readme-contains-glossary` #](#-readme-contains-glossary-)
    - [✅ `readme-contains-policies` #](#-readme-contains-policies-)
    - [✅ `readme-contains-open-source-policy` #](#-readme-contains-open-source-policy-)
    - [✅ `readme-contains-security-and-responsible-disclosure-policy` #](#-readme-contains-security-and-responsible-disclosure-policy-)
    - [✅ `readme-contains-public-domain` #](#-readme-contains-public-domain-)
    - [✅ `contributing-contains-how-to-contribute` #](#-contributing-contains-how-to-contribute-)
    - [✅ `contributing-contains-getting-started` #](#-contributing-contains-getting-started-)
    - [✅ `contributing-contains-workflow-and-branching` #](#-contributing-contains-workflow-and-branching-)
    - [✅ `contributing-contains-testing-conventions` #](#-contributing-contains-testing-conventions-)
    - [✅ `contributing-contains-coding-style-and-linters` #](#-contributing-contains-coding-style-and-linters-)
    - [✅ `contributing-contains-writing-issues` #](#-contributing-contains-writing-issues-)
    - [✅ `contributing-contains-documentation` #](#-contributing-contains-documentation-)
    - [✅ `contributing-contains-policies` #](#-contributing-contains-policies-)
    - [✅ `contributing-contains-open-source-policy` #](#-contributing-contains-open-source-policy-)
    - [✅ `contributing-contains-security-and-responsible-disclosure-policy` #](#-contributing-contains-security-and-responsible-disclosure-policy-)
    - [✅ `contributing-contains-public-domain` #](#-contributing-contains-public-domain-)
  - [Ignored #](#ignored-)
    - [`maintainers-file-exists` #](#maintainers-file-exists-)
    - [`codeowners-file-exists` #](#codeowners-file-exists-)
    - [`governance-file-exists` #](#governance-file-exists-)
    - [`community-guidelines-file-exists` #](#community-guidelines-file-exists-)
    - [`code-of-conduct-file-exists` #](#code-of-conduct-file-exists-)
    - [`readme-contains-project-vision` #](#readme-contains-project-vision-)
    - [`readme-contains-governance` #](#readme-contains-governance-)
    - [`contributing-contains-team-specific-guidelines` #](#contributing-contains-team-specific-guidelines-)
    - [`contributing-contains-writing-pull-requests` #](#contributing-contains-writing-pull-requests-)
    - [`contributing-contains-reviewing-pull-requests` #](#contributing-contains-reviewing-pull-requests-)
    - [`contributing-contains-shipping-releases` #](#contributing-contains-shipping-releases-)
    - [`maintainers-contains-maintainers` #](#maintainers-contains-maintainers-)
    - [`maintainers-contains-maintainers-list` #](#maintainers-contains-maintainers-list-)
    - [`maintainers-contains-approvers-list` #](#maintainers-contains-approvers-list-)
    - [`maintainers-contains-reviewers-list` #](#maintainers-contains-reviewers-list-)
    - [`governance-contains-governance` #](#governance-contains-governance-)
    - [`code-owners-contains-list-of-users` #](#code-owners-contains-list-of-users-)
    - [`code-owners-contains-repo-domains` #](#code-owners-contains-repo-domains-)
    - [`community-guidelines-contains-principles` #](#community-guidelines-contains-principles-)
    - [`community-guidelines-contains-community-guidelines` #](#community-guidelines-contains-community-guidelines-)
    - [`community-guidelines-contains-acknowledgements` #](#community-guidelines-contains-acknowledgements-)
    - [`code-of-conduct-contains-contributor-code-of-conduct` #](#code-of-conduct-contains-contributor-code-of-conduct-)
    - [`code-of-conduct-contains-acknowledgements` #](#code-of-conduct-contains-acknowledgements-)
    - [Review Repository Details](#review-repository-details)
    - [Additional Notes \& Questions](#additional-notes--questions)
    - [Sign off on risk acceptance of open-sourcing the software product](#sign-off-on-risk-acceptance-of-open-sourcing-the-software-product)
    - [Flipping the Switch: Making the Repository Public](#flipping-the-switch-making-the-repository-public)

## Fail <a href="#user-content-fail" id="fail">#</a>

### ❌ `contributing-contains-building-dependencies` <a href="#user-content--contributing-contains-building-dependencies" id="-contributing-contains-building-dependencies">#</a>

Doesn't contain Building dependencies (`CONTRIBUTING.md`).

### ❌ `contributing-contains-building-the-project` <a href="#user-content--contributing-contains-building-the-project" id="-contributing-contains-building-the-project">#</a>

Doesn't contain Building the Project (`CONTRIBUTING.md`).


## Warning <a href="#user-content-warning" id="warning">#</a>

<details>
<summary>Click to see rules</summary>

### ⚠️ `readme-contains-development-and-software-delivery-lifecycle` <a href="#user-content--readme-contains-development-and-software-delivery-lifecycle" id="-readme-contains-development-and-software-delivery-lifecycle">#</a>

Doesn't contain Development and Software Delivery Lifecycle (`README.md`).

### ⚠️ `readme-contains-local-development` <a href="#user-content--readme-contains-local-development" id="-readme-contains-local-development">#</a>

Doesn't contain Local Development (`README.md`).

</details>

## Passed <a href="#user-content-passed" id="passed">#</a>

<details>
<summary>Click to see rules</summary>

### ✅ `license-file-exists` <a href="#user-content--license-file-exists" id="-license-file-exists">#</a>

Found file (`LICENSE`).

### ✅ `security-file-exists` <a href="#user-content--security-file-exists" id="-security-file-exists">#</a>

Found file (`SECURITY.md`).

### ✅ `readme-file-exists` <a href="#user-content--readme-file-exists" id="-readme-file-exists">#</a>

Found file (`README.md`).

### ✅ `contributing-file-exists` <a href="#user-content--contributing-file-exists" id="-contributing-file-exists">#</a>

Found file (`CONTRIBUTING.md`).

### ✅ `license-contains-license` <a href="#user-content--license-contains-license" id="-license-contains-license">#</a>

Contains license (`LICENSE`).

### ✅ `security-contains-security-and-responsible-disclosure-policy` <a href="#user-content--security-contains-security-and-responsible-disclosure-policy" id="-security-contains-security-and-responsible-disclosure-policy">#</a>

Contains Security and Responsible Disclosure Policy (`SECURITY.md`).

### ✅ `readme-contains-about-the-project` <a href="#user-content--readme-contains-about-the-project" id="-readme-contains-about-the-project">#</a>

Contains About the Project (`README.md`).

### ✅ `readme-contains-project-mission` <a href="#user-content--readme-contains-project-mission" id="-readme-contains-project-mission">#</a>

Contains Project Mission (`README.md`).

### ✅ `readme-contains-agency-mission` <a href="#user-content--readme-contains-agency-mission" id="-readme-contains-agency-mission">#</a>

Contains Agency Mission (`README.md`).

### ✅ `readme-contains-team-mission` <a href="#user-content--readme-contains-team-mission" id="-readme-contains-team-mission">#</a>

Contains Team Mission (`README.md`).

### ✅ `readme-contains-core-team` <a href="#user-content--readme-contains-core-team" id="-readme-contains-core-team">#</a>

Contains Core Team (`README.md`).

### ✅ `readme-contains-documentation-index` <a href="#user-content--readme-contains-documentation-index" id="-readme-contains-documentation-index">#</a>

Contains Documentation Index (`README.md`).

### ✅ `readme-contains-repository-structure` <a href="#user-content--readme-contains-repository-structure" id="-readme-contains-repository-structure">#</a>

Contains Repository Structure (`README.md`).

### ✅ `readme-contains-coding-style-and-linters` <a href="#user-content--readme-contains-coding-style-and-linters" id="-readme-contains-coding-style-and-linters">#</a>

Contains Coding Style and Linters (`README.md`).

### ✅ `readme-contains-branching-model` <a href="#user-content--readme-contains-branching-model" id="-readme-contains-branching-model">#</a>

Contains Branching Model (`README.md`).

### ✅ `readme-contains-contributing` <a href="#user-content--readme-contains-contributing" id="-readme-contains-contributing">#</a>

Contains Contributing (`README.md`).

### ✅ `readme-contains-codeowners` <a href="#user-content--readme-contains-codeowners" id="-readme-contains-codeowners">#</a>

Contains Codeowners (`README.md`).

### ✅ `readme-contains-community` <a href="#user-content--readme-contains-community" id="-readme-contains-community">#</a>

Contains Community (`README.md`).

### ✅ `readme-contains-community-guidelines` <a href="#user-content--readme-contains-community-guidelines" id="-readme-contains-community-guidelines">#</a>

Contains Community Guidelines (`README.md`).

### ✅ `readme-contains-feedback` <a href="#user-content--readme-contains-feedback" id="-readme-contains-feedback">#</a>

Contains Feedback (`README.md`).

### ✅ `readme-contains-glossary` <a href="#user-content--readme-contains-glossary" id="-readme-contains-glossary">#</a>

Contains Glossary (`README.md`).

### ✅ `readme-contains-policies` <a href="#user-content--readme-contains-policies" id="-readme-contains-policies">#</a>

Contains Policies (`README.md`).

### ✅ `readme-contains-open-source-policy` <a href="#user-content--readme-contains-open-source-policy" id="-readme-contains-open-source-policy">#</a>

Contains Open Source Policy (`README.md`).

### ✅ `readme-contains-security-and-responsible-disclosure-policy` <a href="#user-content--readme-contains-security-and-responsible-disclosure-policy" id="-readme-contains-security-and-responsible-disclosure-policy">#</a>

Contains Security and Responsible Disclosure Policy (`README.md`).

### ✅ `readme-contains-public-domain` <a href="#user-content--readme-contains-public-domain" id="-readme-contains-public-domain">#</a>

Contains Public domain (`README.md`).

### ✅ `contributing-contains-how-to-contribute` <a href="#user-content--contributing-contains-how-to-contribute" id="-contributing-contains-how-to-contribute">#</a>

Contains How to Contribute (`CONTRIBUTING.md`).

### ✅ `contributing-contains-getting-started` <a href="#user-content--contributing-contains-getting-started" id="-contributing-contains-getting-started">#</a>

Contains Getting Started (`CONTRIBUTING.md`).

### ✅ `contributing-contains-workflow-and-branching` <a href="#user-content--contributing-contains-workflow-and-branching" id="-contributing-contains-workflow-and-branching">#</a>

Contains Workflow and Branching (`CONTRIBUTING.md`).

### ✅ `contributing-contains-testing-conventions` <a href="#user-content--contributing-contains-testing-conventions" id="-contributing-contains-testing-conventions">#</a>

Contains Testing Conventions (`CONTRIBUTING.md`).

### ✅ `contributing-contains-coding-style-and-linters` <a href="#user-content--contributing-contains-coding-style-and-linters" id="-contributing-contains-coding-style-and-linters">#</a>

Contains Coding Style and Linters (`CONTRIBUTING.md`).

### ✅ `contributing-contains-writing-issues` <a href="#user-content--contributing-contains-writing-issues" id="-contributing-contains-writing-issues">#</a>

Contains ISSUE_TEMPLATE.md | Issues (`CONTRIBUTING.md`).

### ✅ `contributing-contains-documentation` <a href="#user-content--contributing-contains-documentation" id="-contributing-contains-documentation">#</a>

Contains Documentation (`CONTRIBUTING.md`).

### ✅ `contributing-contains-policies` <a href="#user-content--contributing-contains-policies" id="-contributing-contains-policies">#</a>

Contains Policies (`CONTRIBUTING.md`).

### ✅ `contributing-contains-open-source-policy` <a href="#user-content--contributing-contains-open-source-policy" id="-contributing-contains-open-source-policy">#</a>

Contains Open Source Policy (`CONTRIBUTING.md`).

### ✅ `contributing-contains-security-and-responsible-disclosure-policy` <a href="#user-content--contributing-contains-security-and-responsible-disclosure-policy" id="-contributing-contains-security-and-responsible-disclosure-policy">#</a>

Contains Security and Responsible Disclosure Policy (`CONTRIBUTING.md`).

### ✅ `contributing-contains-public-domain` <a href="#user-content--contributing-contains-public-domain" id="-contributing-contains-public-domain">#</a>

Contains Public domain (`CONTRIBUTING.md`).

</details>

## Ignored <a href="#user-content-ignored" id="ignored">#</a>

<details>
<summary>Click to see rules</summary>

### `maintainers-file-exists` <a href="#user-content-maintainers-file-exists" id="maintainers-file-exists">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `codeowners-file-exists` <a href="#user-content-codeowners-file-exists" id="codeowners-file-exists">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `governance-file-exists` <a href="#user-content-governance-file-exists" id="governance-file-exists">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `community-guidelines-file-exists` <a href="#user-content-community-guidelines-file-exists" id="community-guidelines-file-exists">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `code-of-conduct-file-exists` <a href="#user-content-code-of-conduct-file-exists" id="code-of-conduct-file-exists">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `readme-contains-project-vision` <a href="#user-content-readme-contains-project-vision" id="readme-contains-project-vision">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `readme-contains-governance` <a href="#user-content-readme-contains-governance" id="readme-contains-governance">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `contributing-contains-team-specific-guidelines` <a href="#user-content-contributing-contains-team-specific-guidelines" id="contributing-contains-team-specific-guidelines">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `contributing-contains-writing-pull-requests` <a href="#user-content-contributing-contains-writing-pull-requests" id="contributing-contains-writing-pull-requests">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `contributing-contains-reviewing-pull-requests` <a href="#user-content-contributing-contains-reviewing-pull-requests" id="contributing-contains-reviewing-pull-requests">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `contributing-contains-shipping-releases` <a href="#user-content-contributing-contains-shipping-releases" id="contributing-contains-shipping-releases">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `maintainers-contains-maintainers` <a href="#user-content-maintainers-contains-maintainers" id="maintainers-contains-maintainers">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `maintainers-contains-maintainers-list` <a href="#user-content-maintainers-contains-maintainers-list" id="maintainers-contains-maintainers-list">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `maintainers-contains-approvers-list` <a href="#user-content-maintainers-contains-approvers-list" id="maintainers-contains-approvers-list">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `maintainers-contains-reviewers-list` <a href="#user-content-maintainers-contains-reviewers-list" id="maintainers-contains-reviewers-list">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `governance-contains-governance` <a href="#user-content-governance-contains-governance" id="governance-contains-governance">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `code-owners-contains-list-of-users` <a href="#user-content-code-owners-contains-list-of-users" id="code-owners-contains-list-of-users">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `code-owners-contains-repo-domains` <a href="#user-content-code-owners-contains-repo-domains" id="code-owners-contains-repo-domains">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `community-guidelines-contains-principles` <a href="#user-content-community-guidelines-contains-principles" id="community-guidelines-contains-principles">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `community-guidelines-contains-community-guidelines` <a href="#user-content-community-guidelines-contains-community-guidelines" id="community-guidelines-contains-community-guidelines">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `community-guidelines-contains-acknowledgements` <a href="#user-content-community-guidelines-contains-acknowledgements" id="community-guidelines-contains-acknowledgements">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `code-of-conduct-contains-contributor-code-of-conduct` <a href="#user-content-code-of-conduct-contains-contributor-code-of-conduct" id="code-of-conduct-contains-contributor-code-of-conduct">#</a>

This rule was ignored for the following reason: ignored because level is "off"

### `code-of-conduct-contains-acknowledgements` <a href="#user-content-code-of-conduct-contains-acknowledgements" id="code-of-conduct-contains-acknowledgements">#</a>

This rule was ignored for the following reason: ignored because level is "off"

</details>

**Running repolinter on your repository via GitHub Actions**

1. Add the tier-specific [checks.yml](https://github.com/DSACMS/repo-scaffolder/blob/main/tier1/%7B%7Bcookiecutter.project_slug%7D%7D/.github/workflows/checks.yml) to the github directory of your project. The file includes a job that runs a repolinter called [repolinter-checks](https://github.com/DSACMS/repo-scaffolder/blob/main/tier1/%7B%7Bcookiecutter.project_slug%7D%7D/.github/workflows/checks.yml#L13)

2. Manually trigger the workflow

3. The results produces an issue on the repository with a list of file and section existence checks, indicating whether each requirement was met or not


 **Review Content**

 The project should include the following files and sections [(link to template)](https://github.com/DSACMS/repo-scaffolder/tree/main/tier1/%7B%7Bcookiecutter.project_slug%7D%7D):

 - [x] **README.md**
    _An essential guide that gives viewers a detailed description of your project_




| **Section**         | **Description**                                                                                                                                                                                                                                                                                | **Included** |
|---------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| Project Description | 1-3 sentences short description of the project that can be used as a 'one-liner' to describe the repo. A best practice is using this same language as the official 'description' on GitHub repo landing page.                                                                                  |    :white_check_mark: :x:          |
| About the Project   | Longer-form description of the project. It can include history, background, details, problem statements, links to design documents or other supporting materials, or any other information/context that a user or contributor might be interested in.                                             |              |
| Core Team           | This information helps with succession planning and provenance for security compliances and remediation. It helps future users and contributors understand where the code originated.                                                                                                          |              |
| Policies            | This section is to explicitly link to Federal policies and guidelines that are required or rocommended for Federal projects to comply with, such as Accessibility (508) Interoperability, Anti-deficiency, Security, Licensing, and other policies that can vary between agencies and domains. |              |
| Public Domain       | A best practice is to list the LICENSE under which a project is released at the bottom of the README. In most cases for Federal repos, we default to Creative Commons Zero 1.0 International(world-wide public domain.)                                                                        |              |


- [X] **LICENSE**

*License of your project, whether public domain (CC0) or other OSI-approved License. Using 'vanilla' license text will allow for GitHub to auto-label the license information on the repository landing page.*

- [X] **CONTRIBUTING.md**
*Provide guidance on how users can run your project and make contributions to it.*

| **Section**           | **Description**                                                                                                                                                                                                                                                                                     | **Included** |
|-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| Getting Started       | Included installations steps, prerequisites for installation, and instructions for working with the source code                                                                                                                                                                                     |              |
| Building Dependencies | This step is often skipped, so don't forget to include the steps needed to install on your platform. If your project can be multi-platform, this is an excellent place for first time contributors to send patches!                                                                                 |              |
| Building the Project  | Be sure to include build scripts and instructions, not just the source code itself!                                                                                                                                                                                                                 |              |
| Writing Issues        | Make a brief statement about where to file issues, and conventions for doing so.                                                                                                                                                                                                                    |              |
| Policies              | This section is here to explicitly link to Federal policies and guidelines that are required or recommended for Federal projects to comply with, such as Accessibility (508) Interoperability, Anti-deficiency, Security, Licensing, and other policies that can vary between agencies and domains. |              |
| Public Domain         | This section is to explicitly link to Federal policies and guidelines that required or recommended for Federal projects to comply with, such as Accessibility (508) Interoperability, Anti-deficiency, Security, Licensing, and other policies that can vary between agencies and domains.          |              |

- [X] **repolinter.json**
_Lints repository for missing files and sections above_

**Results**

*All neccesasary components are present.*


### Review Repository Details

The GitHub repository homepage features a concise description of the project, a list of relevant topic tags, and general information about the repository to provide a comprehensive overview for users and contributors.

_About Section_
- [X] **Description**
1-2 sentences describing the project

- [ ] **Website**
Link to project's website

- [ ] **Topics**
Tags for project discoverability. Helpful topics to classify a repository include the repository's intended purpose, subject area, community, or language.

_Include in Home Page_:

- [ ] Releases
- [ ] Packages
- [ ] Deployments



**Results**

*Although there are is information missing from this section, I believe the descripition is all that is needed in this specifc case.*


### Additional Notes & Questions

*This repo for the most part is ready to be outbounded and has been properly reviewed.*


### Sign off on risk acceptance of open-sourcing the software product

After reviewing the materials prepared by the team that is working to open source the product, the business owner signs off on a risk acceptance for open-sourcing the software product.


Requesting sign off from key people on this request.


| **Reviewer Organization**      | **Reviewer Name**                                  | Reviewer's Recommendation**                                                     |
|--------------------------------|----------------------------------------------------|---------------------------------------------------------------------------------|
| Code Reviewer's Recommendation | CODE REVIEWER 1  CODE REVIEWER 2   CODE REVIEWER 3 | [Approved/Needs Approval]  [Approved/Needs Approval]  [Approved/Needs Approval] |
| ISSO                           | ISSO REVIEWER                                      | [Approved/Needs Approval]                                                       |
| ISG Technical Approval         | ISG REVIEWER                                       | [Approved/Needs Approval]                                                       |
| Business Owner(s)              | BUSINESS OWNER 1  BUSINESS OWNER 2                 | [Approved/Needs Approval]  [Approved/Needs Approval]                            |


### Flipping the Switch: Making the Repository Public

Once the repository has passed outbound review, we are ready “flip the switch” and officially make it public. Once made public, there are a couple of actions that need to be taken: 

*Repository Actions* 

Please enable the following features to enhance repository security and maintain code quality:

- [ ] **Dependabot Alerts**
A GitHub Feature. Get notified when one of your dependencies has a vulnerability

- [ ] **Secret Scanning Alerts**
A GitHub Feature. Get notified when a secret is pushed to this repository. Ideally set this up to run after each new commit is pushed to the repository

- [ ] **Branch Protection**
Ensures the Integrity of important branches by preventing unauthorized actions like force pushes and requiring pull request reviews with specific checks before merging. Dev and main should be protected branches in the repository.

- [ ] **Git Branching**
After making the repository public, make sure there is a coherent git branching pla in place. For example: agree to merge features related pull requests into dev but merge bug fixes into main instead of dev first.

[^1]: theres a couple of links

- [ ] **Add Repolinter GH Action to CI**
For ongoing adherence to repository hygiene standards, integrate the [repolinter Github Action](https://github.com/DSACMS/metrics/blob/main/.github/workflows/checks.yml) into your CI pipeline. This addition enhances your workflow by automatically enforcing repository cleanliness standards.

- [ ] **Optional: DCO (Developer Certificate of Origin)**
Requires all commit messages to contain the <span style="color:green"><i>Signed-off-by</i></span> line with an email address that matches the commit author. The Developer Certificate of Origin (DCO) is a lightweight way for contributors to certify that they wrote or otherwise have the right to submit the code they are contributing to the project. The GitHub app to enforce DCO can be found [here](https://github.com/apps/dco) 

_Communications & Rollout :mega:_


Share the good news with communities both inside and outside CMS!

- [ ] **Draft a launch announcement**

Be sure to include the following information:

- Repo Description
  - Repo URL
  - Authoring Team Email Contact
  - Authoring Team URL
  - Authoring Team Slack Channel
  - Call to action (File issues, contribute PRs)

- [ ] **Post launch announcement to CMS slack channel**

  - #cms-opensource
  - #cms-api-community
  - #cms-data-community
  - #cms-engineering-community
  - #ai-community

- [ ] **Send a launch announcement email**

- [ ] **Add launch announcement to a Confluence Wiki Page**

*Tracking* :chart_with_upwards_trend:

Add your project to our inventories.

- [ ] **Add to https://github.com/dsacms/open projects inventory**

- [ ] **Add code.json to repository and sent over a pull request to [code.gov](https://code.gov/)**






