---
layout: home
permalink: index.html

# Please update this with your repository name and project title
repository-name: eYY-co2060-project-template
title: Project Template
---

[comment]: # "This is the standard layout for the project, but you can clean this and use your own template, and add more information required for your own project"

<!-- Once you fill the index.json file inside /docs/data, please make sure the syntax is correct. (You can use this tool to identify syntax errors)

Please include the "correct" email address of your supervisors. (You can find them from https://people.ce.pdn.ac.lk/ )

Please include an appropriate cover page image ( cover_page.jpg ) and a thumbnail image ( thumbnail.jpg ) in the same folder as the index.json (i.e., /docs/data ). The cover page image must be cropped to 940×352 and the thumbnail image must be cropped to 640×360 . Use https://croppola.com/ for cropping and https://squoosh.app/ to reduce the file size.

If your followed all the given instructions correctly, your repository will be automatically added to the department's project web site (Update daily)

A HTML template integrated with the given GitHub repository templates, based on github.com/cepdnaclk/eYY-project-theme . If you like to remove this default theme and make your own web page, you can remove the file, docs/_config.yml and create the site using HTML. -->

# ChronoCampus(University Schedule and Facility Management System.)

---

## Team
-  E/23/392, Thanush V., [email](e23392@eng.pdn.ac.lk)
-  E/23/384, S.Simasa, [email](e23384@eng.pdn.ac.lk)
-  E/23/256, Paveenan S., [email](e23256@eng.pdn.ac.lk)
-  E/23/352, N.A.Sara, [email](e23352@eng.pdn.ac.lk)


<!-- Image (photo/drawing of the final hardware) should be here -->

<!-- This is a sample image, to show how to add images to your page. To learn more options, please refer [this](https://projects.ce.pdn.ac.lk/docs/faq/how-to-add-an-image/) -->

<!-- ![Sample Image](./images/sample.png) -->

#### Table of Contents
1. [Introduction](#introduction)
2. [Solution Architecture](#solution-architecture )
3. [Software Designs](#hardware-and-software-designs)
4. [Testing](#testing)
5. [Conclusion](#conclusion)
6. [Links](#links)

## Introduction

This project focuses on developing a centralized Smart University Schedule and Facility Management System. Universities face challenges such as timetable conflicts, delayed schedule updates, inefficient room usage, and lack of visibility of staff locations. The aim of this system is to provide students, academic staff, and administrators with real-time access to academic schedules, facility availability, and staff location information through a single platform.


## Solution Architecture

The system follows a client-server architecture. A web-based frontend interacts with a RESTful backend through secure APIs. The backend handles authentication, schedule management, facility reservations, notifications, and data storage. Modular components ensure scalability and ease of maintenance. Git-based version control supports collaborative development using feature branches and pull requests.

## Software Designs

The software design is based on a layered architecture. The backend includes separate layers for models, routes, services, and controllers. Database entities include users, schedules, rooms, reservations, and staff locations. The frontend presents dashboards, daily timetables, search interfaces, and notification views. ER diagrams, sequence diagrams, and system diagrams support the design.

## Testing

Testing includes unit testing of backend modules, API endpoint testing, and basic integration testing. Manual testing validates schedule updates, notifications, and room search functionality. Testing ensures reliability, correctness, and error-free execution of the Minimum Viable Product.

## Conclusion

The system improves academic coordination, transparency, and resource utilization within the university. It provides a scalable foundation that can be extended with analytics, mobile support, and advanced orchestration features in future iterations.

## Links

- [Project Repository](https://github.com/cepdnaclk/e23-co2060-ChronoCampus.git){:target="https://github.com/cepdnaclk/e23-co2060-ChronoCampus.git"}
- [Project Page](https://cepdnaclk.github.io/e23-co2060-ChronoCampus/){:target="https://cepdnaclk.github.io/e23-co2060-ChronoCampus/"}
- [Department of Computer Engineering](http://www.ce.pdn.ac.lk/)
- [University of Peradeniya](https://eng.pdn.ac.lk/)

[//]: # (Please refer this to learn more about Markdown syntax)
[//]: # (https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet)
