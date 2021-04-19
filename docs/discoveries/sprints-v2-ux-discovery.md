# Sprints v2 - UX Discovery

## Introduction

The [Sprints][sprints-application] application was developed to manage OpenCraft’s internal time budgeting and planning needs. Now that Sprints has been running for a while, it’s time to move onto the next phase. 

The goals for Phase 2 include:

- Announcing Sprints and discussing it with the open source community
- Developing partnerships with organisations who might find the tool useful
- Getting feedback from Sprint’s current users 
- Using internal and external feedback to refine the project direction
- Improving the usability (UX) of the application
- Developing a user interface (UI) design style for Sprints
- Adding certain features to the current application
- Turning Sprints into a SaaS product

Using the [development discovery][sprints-v2-discovery] as a basis, this document outlines the UX and UI approach that will be taken in order to achieve these goals. It also provides the number of UX/UI hours we estimate will be required each month.

## Proposed Steps

Below is an outline of the steps we expect to follow during Phase 2. We’ll be taking an iterative project approach, meaning that the steps, as well as the order in which they are completed, is likely to change. These adjustments may be made based on a number of factors, including user feedback, new ideas, unexpected realisations etc.

**Please note**: although we have only inserted one round of usability testing into the list below, future rounds will be conducted throughout the project as user feedback becomes necessary.

---

### 1. Paid Plans

Determine the Sprints business model by deciding what billing options to offer users, and how to structure the pricing plans. 
 
The pricing model could be very simple in the beginning (e.g. a paid monthly plan with a free trial). Additionally, billing could be handled manually to start, with invoices being generated in Freshbooks. 

---
 
### 2. Marketing Site 
 
Build a landing page that describes Sprints, outlines its features, and explains its pricing plans. Interested users will be encouraged to enter their email addresses to be added to a waiting list.
 
The marketing site will be built upon as time goes by, with new pages and information being added as the project progresses. Eventually the site will allow users to either create an account, or view the documentation should they wish to install the application themselves. See how [Chatwoot][chatwoot-pricing-plans] (another open source SaaS product) communicates their self-hosted option to their users.

---

### 3. Community Feedback

Rely on the wisdom of the Open Source community by requesting their feedback on the current [Sprints][sprints-application] application, as well as the plan for future phases. The accompanying marketing site will help to give Sprints credibility as a serious project.  
 
List Sprints on open source directories like [AlternativeTo][alternative-to], and contact other open-source projects for their insights. Where possible, it would be valuable to develop partnerships with organisations who need the tool, where we offer them access to Sprints in exchange for their feedback. Although this would require setting up a separate instance for each organisation, it will likely be worth the effort. Getting feedback early on in the development cycle is really valuable.

---

### 4. Remote Usability Testing

Conduct a round of remote usability testing on the Sprints application. The main goal of this round of usability testing is to get feedback about the current user experience. As such, it makes sense to stick to internal users who have already had experience working with the app. We will therefore recruit at least 5 users from Serenity, Bebop, or Falcon to participate in the first round of testing.

Remote usability tests are video-based and include a number of tasks and/or questions. Participants are encouraged to record themselves and their screen (using a service like [Loom][loom-application]), and voice their thoughts as they interact with the application.

Once all the usability tests have been conducted, we will evaluate the videos and provide feedback on the key points. The findings will then guide the direction of the project.

---

### 5. Make Initial UX and UI Improvements

Identify and implement some “quick gains” that would improve the user experience (UX) and user interface (UI) design of the current Sprints app. Although small, these initial UX and UI improvements will not only make internal processes smoother, but will also help to make the tool more attractive to external users.

Initial improvements will be based on:

- feedback from the Open Source community
- findings from the usability tests
- suggestions by Fixate
- improvements suggested in the [development discovery][sprints-v2-discovery], namely:
  - remove unnecessary toggles to make the interface less confusing
  - improve the UX when changing dates
  - improve error handling
  - determine the best UX for the Sustainability and Sprints dashboards
  - investigate how best to manage automatic sprint completion

---

### 6. Larger UX/UI Rework and Style Guide Development

Once the initial UX improvements have been made, time will be dedicated to identifying and implementing larger improvements to the user experience. These updates can be tackled iteratively. 
 
Additionally, the “quick win” UI improvements made in the previous step will be expanded upon to develop a fully-fledged UI design for Sprints. To ensure a cohesive style is applied across the application, Fixate will develop a style guide of design elements for developers to follow. The style guide will be continuously updated and extended as the project progresses.

---

### 7. Budget Enhancements

Ensure that Sprints accounts for different types of client budgets in a user-friendly and accessible manner. Budget types include:

- Multi-account budgets
- Monthly caps
- Cell budgets
- Fixed budgets

---

### 8. Sustainability Ratio of Upcoming Sprint

It would be useful to users to be able to see the sustainability ratio of the upcoming sprint. This ratio is determined from the division of billable, versus non-billable tasks scheduled for the sprint. Determine how to add this feature without cluttering the interface.

---

### 9. Sustainability Predictions

Determine an intuitive way to add predictions to the Sustainability dashboard. Predictions indicate the forecasted sustainability of a sprint by assuming that 100% of defined budgets will be used during the selected date range.

---

### 10. Profile Management

User registration and login has already been implemented on Sprints, however there is currently no way for users to adjust their profile details, or invite other users to the application. Add these features, and determine whether the user experience of the current registration and login could be improved.

---

### 11. Organisations and Roles

Allow users to create organisation/s and invite other members. Implement the following user roles to grant users specific permissions:

- Team Manager
  - User can configure their site, invite new members, manage members, allocate roles, complete sprints
- Epic Owner
  - User can add and modify budgets within their team
- Member
  - User can view the Sprint, Sustainability, and Budget Dashboards, create sprints, schedule tickets

Provide users with an easy way to switch between accounts should they be associated with more than one organisation.

---

### 12. Plugins

One of Sprint’s long-term goals is to become a “fully pluggable” application which allows external users to install their own extensions. However, there are a number of steps to complete before we achieve this.

Here is a breakdown of the steps that could be followed to get us closer to the end-goal:

- Engage with our user base to get feedback on the type of plugins and extensions they would like to be able to install (this includes issue trackers)
- Based on user feedback, determine which issue trackers to support (Sprints currently supports an older version of Jira)
- Investigate how these issue trackers are currently being used by other organisations
- Add plugin capabilities, as well as support for issue trackers iteratively. An example approach:
  - Add support for a newer version of Jira
  - Add GitLab support
  - Install custom plugins manually into the platform on behalf of users
  - Add support for custom plugins, where Team Managers may add their own git link
  - Potentially add a plugin marketplace for Sprints

---

## Monthly UX Time Commitment

We estimate a total of **100 - 160 hours** per month will be required for the UX and UI portion of this project.

**Please note:**

- There are a number of OpenCraft projects scheduled for 2021 (Workflow Manager, Open edX Theming, Sprints v2, Billing v2...) The way in which monthly UX hours are allocated can be determined by the priority of the projects.
- Usability testing may incur additional 3rd party costs if we are required to recruit external test users.

## Project Roles

- Product management: Fixate (Ali/Cassie), reviewed by Xavier
- Reviewers on UX/UI tasks: Xavier Antoviaque and Developers
- 2nd reviewers on development tasks: Fixate (Ali/Cassie)

<!-- LINKS -->

[sprints-application]: https://sprints.opencraft.com/
[sprints-v2-discovery]: https://gitlab.com/opencraft/dev/sprints/-/blob/74e95b1c68a9cf2a510d7ef3cdea6dde7cd9468a/docs/discoveries/1.%20Sprints%20v2.md
[chatwoot-pricing-plans]: https://www.chatwoot.com/pricing/
[alternative-to]: https://alternativeto.net/software/ifttt/?license=opensource
[loom-application]: https://www.loom.com/
