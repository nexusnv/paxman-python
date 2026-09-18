DOI HANDBOOK

DOI HANDBOOK 1 DOI Foundation Publication date: September 2025 COPYRIGHT
LICENSE AGREEMENT This work is released under a CC BY-ND license, which
means that you are free to do with it as you please as long as you (1)
properly attribute it and (2) do not create derivative works. © 2025 DOI
Foundation TRADEMARK AND LOGO USAGE POLICY DOI®, DOI.ORG® and shortDOI®
are registered trademarks of the DOI® Foundation. The DOI® Foundation
authorizes users who correctly implement International Standard ISO
26324 to use the trademark free of charge to indicate such
implementation; however, this authorization applies only and exclusively
in the context of such use. The DOI® Foundation is willing to authorize
anyone who creates software or other products or services implementing
ISO 26324 to use the trademark DOI free of charge provided that: • the
software, product or service is accurately described • DOI is identified
as a trademark of the DOI® Foundation • the superscript symbol ® is
placed following the letters "DOI" at its first occurrence in any
printed or electronic document describing or marketing the software,
product or service A re-sizable version of the DOI logo for Internet use
under these conditions can be downloaded from the DOI® web site as a
convenience for companies, organizations and the press. Inclusion of
this logo should not be used to imply DOI® Foundation's endorsement of
the company, product or services. For more information, see the
Trademark Policy
(https://www.doi.org/resources/130718-trademark-policy.pdf).

DOI HANDBOOK 2 CONTENTS CHAPTER 1. DOI System Overview
......................................................................................................
1.1. History and Purpose of the DOI System
................................................................................................
9 1.2. Basic Principle: Integration of Identifier Resolution and
Semantics ........................................................ 9
1.3. Identifier/Resolution System within the Handle System
........................................................................
10 1.3.1. DOI Name: Unique and Persistent Identifier
......................................................................................
10 1.3.2. DOI Name Syntax
..............................................................................................................................
11 1.4. Structured Semantics Based on Strict Principles
..................................................................................
12 1.4.1. Principles of the Metadata Model
......................................................................................................
12 1.4.2. Standard Metadata Declaration
..........................................................................................................
12 1.5. Basic Resolution Services Provided by the DOI System
......................................................................
13 1.5.1. Direct Redirection to a Web Resource with the DOI Proxy
............................................................... 13
1.5.2. Additional Resolution Services Included in the DOI System
.............................................................. 14 1.6.
Value-added Services a Registration Agency can Build on the DOI System
........................................ 14 1.6.1. Management of a
Referent with Several Instances
...........................................................................
15 1.6.2. Dynamic Building of a Web Page Enriched with Metadata
................................................................ 15 1.7.
Business and Organizational Model of the DOI System
.......................................................................
16 1.7.1. Federation of Registration Agencies (RA)
.........................................................................................
16 1.7.2. Free Resolution Service
.....................................................................................................................
16 1.7.3. Governance Role of the DOI Foundation
..........................................................................................
17 1.7.4. DOI Namespace Allocation Approach
................................................................................................
17 1.8. Standardization of the DOI System
......................................................................................................
18 1.8.1. ISO 26324
..........................................................................................................................................
18 1.8.2. Conformance with Relevant External Standards
................................................................................
19 1.9. Persistence as a Design Feature of the DOI System
...........................................................................
19 1.10. Benefits of the DOI System
................................................................................................................
20 1.10.1. Improved Content Management and Discovery
...............................................................................
21 1.10.2. Solution to the Broken Link (Persistence)
........................................................................................
21 1.10.3. Identifier Interoperability through a Powerful Metadata Model
......................................................... 21 1.10.4.
Compatibility with other Identifier Systems
......................................................................................
21 1.10.5. Service Flexibility and Extensibility
..................................................................................................
22 1.10.6. Protected and Trusted Information
...................................................................................................
22 1.10.7. Information Traceability
....................................................................................................................
22 1.11. Application Examples of the DOI System
...........................................................................................
22 CHAPTER 2. DOI System Governance and Participation
......................................................................
2.1. DOI System Governance Body: The DOI Foundation
..........................................................................
25 2.1.1. Status of the DOI Foundation
............................................................................................................
25 2.1.2. Overview of the DOI Foundation Roles
.............................................................................................
25 2.1.3. ISO 26324 Registration Authority
.......................................................................................................
25 2.1.4. Representation to Strategic Organizations
.........................................................................................
27 2.1.5. DOI Foundation Membership
.............................................................................................................
27 2.1.6. DOI Foundation Governance
.............................................................................................................
29 2.2. DOI System Participants: Registration Agencies and Registrants
........................................................ 30 2.2.1. Roles
of a Registration Agency
.........................................................................................................
30 2.2.2. Business Model for Registration Agencies
.........................................................................................
30 2.2.3. Service Non-Exclusivity and Competition Matters
..............................................................................
31 2.2.4. RA Agreement
....................................................................................................................................
31 2.2.5. Process of Becoming a Registration Agency
.....................................................................................
32 2.2.6. Fee Structure for Registration Agencies
............................................................................................
32 2.2.7. Registrant Roles and Duties
..............................................................................................................
33 2.3. DOI System Governing Policies
............................................................................................................
33 2.3.1. Policy Formulation Process
................................................................................................................
33 DOI HANDBOOK 3 2.3.2. List of Formal DOI Documents
..........................................................................................................
33 CHAPTER 3. DOI Namespace
...............................................................................................................
3.1. Assignment Principles of the DOI Name
..............................................................................................
37 3.2. Use of Unicode
.....................................................................................................................................
37 3.3. Syntax of the DOI Name
......................................................................................................................
37 3.3.1. DOI Prefix
...........................................................................................................................................
38 3.3.2. DOI Suffix
...........................................................................................................................................
38 3.3.3. Case Insensitivity of the DOI Name
...................................................................................................
38 3.3.4. Considerations about the Use of Check Digits in DOI Names
........................................................... 39 3.4.
Representation Formats
........................................................................................................................
39 3.4.1. Visual Media
.......................................................................................................................................
39 3.4.2. URI Form
............................................................................................................................................
40 3.4.3. URN Form
..........................................................................................................................................
40 3.4.4. HTTP Proxy Form
..............................................................................................................................
40 3.4.5. Other
...................................................................................................................................................
40 3.5. Avoiding and Resolving Ambiguities when Presenting or Exchanging
DOI Names .............................. 40 3.6. UTF-8 Serialization
................................................................................................................................
41 3.7. Percent-Encoding
..................................................................................................................................
41 3.8. Integration of Other Identifier Schemes
................................................................................................
42 3.8.1. Specification of Another Identifier in System Metadata
......................................................................
42 3.8.2. Incorporation of an Existing Identifier into a DOI Name
..................................................................... 42
3.8.3. Linkage of DOI Names to Another Registry
......................................................................................
43 CHAPTER 4. System Metadata
..............................................................................................................
4.1. Introduction to System Metadata
..........................................................................................................
45 4.2. Metadata Requirements According to ISO 26324
................................................................................
46 4.2.1. General Requirements on Metadata
..................................................................................................
46 4.2.2. Requirements on Metadata Functions
...............................................................................................
46 4.2.3. Requirements on Metadata Registration
............................................................................................
46 4.3. System Metadata Model
.......................................................................................................................
47 4.3.1. System Metadata Model Policy
..........................................................................................................
47 4.3.2. DOI System Metadata
........................................................................................................................
48 4.3.3. Additional Metadata
............................................................................................................................
48 4.3.4. Data Model Extension and Maintenance
...........................................................................................
49 4.4. Metadata Interoperability
.......................................................................................................................
49 4.4.1. Motivations for Interoperability
...........................................................................................................
49 4.4.2. Achievement of Interoperability
..........................................................................................................
49 4.5. Automated Integration of Metadata
.......................................................................................................
50 CHAPTER 5. DOI Identifier / Resolution Services
..................................................................................
5.1. Identifier / Resolution Services based on the Handle System
.............................................................. 52 5.1.1.
ISO 26234 Functional Requirements on the Resolution System
....................................................... 52 5.1.2.
Introduction to the Handle Record
.....................................................................................................
52 5.1.3. Handle System Service Architecture
..................................................................................................
53 5.2. DOI Directory
........................................................................................................................................
55 5.2.1. Local Handle Services (LHS) Used in the DOI System
..................................................................... 56
5.2.2. DOI LHS Operated by a Registration Agency
...................................................................................
56 5.3. DOI Resolvers
.......................................................................................................................................
57 5.3.1. DOI Proxy
...........................................................................................................................................
57 5.3.2. Custom DOI Resolvers
......................................................................................................................
58 5.3.3. DOI REST API
...................................................................................................................................
58 5.4. DOI Resolution Functions
.....................................................................................................................
58 5.4.1. Single DOI Resolution
........................................................................................................................
58 5.4.2. Multiple DOI Resolution
.....................................................................................................................
59 5.4.3. Parameter Passing
.............................................................................................................................
59 DOI HANDBOOK 4 5.4.4. Content Negotiation
............................................................................................................................
60 5.4.5. Handling of Resolution Errors in the DOI System
.............................................................................
62 5.5. ShortDOI Service
..................................................................................................................................
62 5.6. Which RA? Service
...............................................................................................................................
63 CHAPTER 6. DOI Applications
...............................................................................................................
6.1. Introduction to DOI Applications
...........................................................................................................
65 6.2. Use and Extension of the Resolution Functions
...................................................................................
65 6.3. Applications of the 10320/LOC Element
...............................................................................................
65 6.3.1. Choose-by Mechanism
.......................................................................................................................
65 6.3.2. Automated Selection of a URL According to Various Criteria
............................................................ 66 6.4.
Redirection to Linked Data Servies
......................................................................................................
68 6.5. Dynamic Identification of the Fragments of an Entity
...........................................................................
69 CHAPTER 7. Designing and Developing a DOI Application
................................................................... 7.1.
Checklist for Designing a DOI Application
............................................................................................
71 7.2. Design Considerations
..........................................................................................................................
72 7.3. Defining an Identifier Scheme
...............................................................................................................
73 7.3.1. Integrating Another Identifier Scheme
................................................................................................
73 7.4. Managing System Metadata Models
.....................................................................................................
74 7.4.1. Creating or Updating a Metadata Model
............................................................................................
74 7.5. Developing a DOI Resolver
..................................................................................................................
74 7.5.1. Developing Handle System Client Software
......................................................................................
74 7.6. Configuring the Resolution Error Message Handling
............................................................................
75 CHAPTER 8. Defining RA and Registrant Policies
.................................................................................
8.1. Defining a Prefix Allocation Policy
........................................................................................................
77 8.2. Defining a Data Maintenance Policy
.....................................................................................................
77 8.3. Defining a DOI Name Registration Policy
.............................................................................................
77 CHAPTER 9. Operating and Maintaining the RA Services
.....................................................................
9.1. Defining Operational Processes
............................................................................................................
79 9.1.1. Defining the DOI Name Registration Process
....................................................................................
79 9.2. Managing the User Accesss Rights
......................................................................................................
79 9.3. Issuing Prefixes to Registrants
.............................................................................................................
79 9.4. Maintaining the Resolution Services
.....................................................................................................
79 9.4.1. Troubleshooting Resolution Problems
................................................................................................
80 9.5. Operating Your Own LHS
.....................................................................................................................
80 9.5.1. Installing the LHS
...............................................................................................................................
80 9.5.2. Setting up the LHS
.............................................................................................................................
80 9.5.3. LHS Operation Requirements
............................................................................................................
80 9.6. Transferring DOI Names from One Registrant to Another
.................................................................... 81
9.7. Transferring DOI Names from One Registration Agency to Another
.................................................... 81 CHAPTER 10.
Appendix
.........................................................................................................................
10.1. System Metadata Model
.....................................................................................................................
83 10.1.1. DOI System Elements
......................................................................................................................
83 10.2. DOI Proxy Query Command Format
...................................................................................................
85 10.3. DOI REST API Request and Response Formats
...............................................................................
86 10.3.1. REST API Response Format
...........................................................................................................
88 10.4. 10320/LOC Element
............................................................................................................................
89 10.4.1. 10320/LOC: XML Attributes
.............................................................................................................
89 10.4.2. 10320/LOC: Example
.......................................................................................................................
91 10.4.3. 10320/LOC at Prefix Level
...............................................................................................................
93 10.5. Prefix Handle Example
........................................................................................................................
94 10.6. System Tools
.......................................................................................................................................
95 CHAPTER 11. Glossary
..........................................................................................................................

DOI HANDBOOK 5 Chapter 0

PREFACE

ABOUT THIS HANDBOOK

The DOI Handbook is the main source of information about the DOI System.
It describes the DOI System at business and technical levels and assists
the community in understanding the system and Registration Agencies (RA)
in providing services based on the system. Other information resources,
such as factsheets and FAQs are available on the web site and are cited
from this handbook where relevant. AUDIENCE This handbook is directed at
anyone who is involved in services provided through the DOI System, or
who is potentially interested in the DOI System: RAs, application
designers and developers, RA communities. ORGANIZATION This handbook
contains the following material: • Chapter 1: DOI System Overview This
chapter introduces the DOI System's history, purpose, basic principles,
benefits and applications. • Chapter 2: DOI System Governance and
Participation This chapter describes the role and functions of the DOI
Foundation and of Registration Agencies within the DOI System. It also
summarizes the policies governing the DOI System and explains the policy
formulation process. • Chapter 3: DOI Namespace This chapter defines the
syntax for a DOI name. It also explains the DOI name assignment
principles and how other identifier schemes can be integrated into the
DOI system. • Chapter 4: System Metadata This chapter explains the basis
for one of the main technical components of the DOI System, the DOI data
model, and its ability to ensure interoperability of DOI name metadata
assigned through metadata schemes. • Chapter 5: DOI Identifier /
Resolution Services This chapter describes the identifier/resolution
services included in the DOI System package. • Chapter 6: DOI
Applications This chapter discusses some of the ways in which resolution
can be harnessed to provide applications with the ability to resolve a
DOI name to the most appropriate content chosen from multiple DOI
resolution options. These options can include pop-up menus offering
manual selection, and consistent automated selection through content
negotiation and Linked Data. • Chapter 7: Designing and Developing a DOI
Application This chapter assists business analysts and developers in
designing and developing applications based on the DOI System. • Chapter
8: Defining RA and Registrant Policies This chapter assists the
Registra-tion Agencies or registrants in defining their own policies.
DOI HANDBOOK 6 • Chapter 9: Operating and Maintaining the RA Services
This chapter assists the Registration Agency's service operations team
in performing service operation tasks. • Appendix • Glossary • Index
STANDARD DOCUMENTS The main standard documents related to the DOI are: •
ISO 26324:2025 "Information and documentation --- Digital object
identifier system" • DOI Foundation, "DOI URI Scheme", doi:10.1000/292 •
The Unicode Consortium, The Unicode Standard,
url:https://www.unicode.org/versions/latest/ • "Digital Object
Identifier Resolution Protocol (DO-IRP) Specification" version 3.0 June
2022. https://
www.dona.net/sites/default/files/2022-06/DO-IRPV3.0--2022-06-30.pdf
Notice: The DOI Foundation welcomes the publication of the Digital
Object Iden-tifier Resolution Protocol (DO-IRP). This specification is
made available by DONA, a Swiss Foundation set up to govern the Handle
System® (as used by the DOI in-frastructure) and promote associated
specifications. The Handle System was previously specified only in
"informative" documents and the publication of proven, normative
documents that remove features that were never implemented will increase
the robustness and reliability of the DOI infrastructure. This
infrastructure is used over 12 billion times a year to resolve over 300
million DOI names across the different sectors that rely on it. Most
users access the DOI in-frastructure through the resilient network of
web proxies at https://doi.org and never encounter the Handle System
directly, but this publication will ensure that the DOI System remains
world-class into the future.

DOI HANDBOOK 7 Chapter 1

DOI SYSTEM OVERVIEW

This chapter introduces the DOI System's history, purpose, basic
principles, benefits and applications.

In This Chapter 2.1 History and Purpose of the DOI System
........................................ 9 2.2 Basic Principle:
Integration of Identifier Resolution and Semantics
..........................................................................................................................
9 2.3 Identifier/Resolution System within the Handle System
.................. 10 2.4 Structured Semantics Based on Strict
Principles ........................... 12 2.5 Basic Resolution Services
Provided by the DOI System ................. 13 2.6 Value-added Services
a Registration Agency can Build on the DOI System
.......................................................................................................................
14 2.7 Business and Organizational Model of the DOI System
................. 16 2.8 Standardization of the DOI System
............................................. 18 2.9 Persistence as a
Design Feature of the DOI System ..................... 19 2.10 Benefits
of the DOI System .....................................................
20 2.11 Application Examples of the DOI System
................................... 22

DOI HANDBOOK 8 2.1 HISTORY AND PURPOSE OF THE DOI SYSTEM The DOI®
(Digital Object Identifier) System originated in a joint initiative of
three trade associations in the publishing industry (International
Publishers Association; International Association of Scientific,
Technical and Medical Publishers; Association of American Publishers).
Although originating in text publishing, the DOI System was conceived as
a generic framework for managing identification of content over digital
networks, recognizing the trend towards digital convergence and
multimedia availability. The system was announced at the Frankfurt Book
Fair 1997. In the same year, the DOI Foundation was created to develop
and manage the DOI System. 2 From its inception the DOI Foundation
worked with the 3 Corporation for National Research Initiatives (CNRI )
as a technical partner, using the Handle System® developed by CNRI as
the digital network component of the DOI System. CNRI remains a
technical partner of the DOI Foundation as the DOI technical support
service provider. The DOI System provides a technical and social
infrastructure on which organizations can build applications to provide
services to users or communities of users. For example, the DOI System
is used in internal processes in multiple industries, for publishing and
reporting across corporate and national boundaries, and in the field of
semantic web applications. Because of the widespread implementation of
the DOI System, the DOI Foundation was invited to propose it as an ISO
standard. ISO 26324 was published in 2012,updated in 2022, and again in
2025. The ISO standard specifies the syntax and operation of the DOI
while leaving implementation issues to the Foundation, which acts as
registration authority for the standard. Note that the DOI Syntax was
originally a National Information Standards Organization (US) standard,
ANSI/NISO Z39.84-2010, first published in 2000 and withdrawn in 2017.

2.2 BASIC PRINCIPLE: INTEGRATION OF IDENTIFIER RESOLUTION AND SEMANTICS
The DOI System provides: • an identification system of entities based on
the Handle System, a globally distributed system for resolving
identifiers Any entity (digital, physical, or abstract) can be
identified by a global unique and persistent identifier called a DOI
name. The DOI name can be resolved to a resource, such as a web or
internet resource, metadata describing the entity, a landing page with
access to further resources, etc. For example, a DOI name representing
an article resolves to the web address of the HTML file version of the
article. • a metadata model Metadata must be assigned to each DOI name
to describe the entity represented by the DOI name. Metadata
interoperability is ensured through basic principles outlined by the DOI
Foundation. Metadata is used to provide services to the users: it can be
displayed to users to enrich an information resource; it can be used by
users to search for a DOI name; etc. The figure below illustrates the
basic principle of the DOI System.

2 3

Further information relating to the involvement of users and potential
users can be found in ... DOI HANDBOOK 9 Figure 1 Basic principle:
integration of identifier resolution and semantics

2.3 IDENTIFIER/RESOLUTION SYSTEM WITHIN THE HANDLE SYSTEM For its
resolution services, the DOI System is an implementation of the Handle
System , a general-purpose distributed information system designed to
provide an efficient, extensible, and secured global name service for
use on networks such as the Internet.

2.3.1 DOI NAME: UNIQUE AND PERSISTENT IDENTIFIER A DOI name is a global
unique identifier of an entity (called the referent). The referent can
be any digital, physical or abstract entity, and it can be defined on
any granularity level of an entity depending on the requirements of the
Registration Agency (RA); and a DOI name may identify a specific edition
of a novel, a novel chapter, a small piece of musical recording, etc.
Referents can be intellectual property where examples would include
inventions, literary and artistic works, ideas, symbols, names, images,
designs, etc. A DOI name can be resolved, through a Handle System
service, to a set of elements, called the DOI record, as illustrated
below. The DOI record usually contains a web address (or URL for Unified
Resource Locator) representing an instance of the referent, and may
contain services such as email, and one or more items of data about the
referent (metadata).

DOI HANDBOOK 10 Figure 2 DOI Name Concept The figure below shows an
example where the referent is the specific edition of a novel. A
referent could also be a chapter of the novel, etc.

Figure 3 DOI record example The DOI name is persistent over time. Its
persistence is provided by the independence of the identifier name from
the element values, in particular from the entity localization or
ownership. These elements can change over time: through the DOI name
resolution, users will always get the up-to-date element values (This
requires that the DOI record data be regularly maintained.). Each
element of the DOI record is assigned an explicit type (for example,
"URL" (web address) or "email"). Predefined types exist in the Handle
System and new types can be added by RAs, making the DOI resolution
system extremely flexible and responsive to new requirements.

2.3.2 DOI NAME SYNTAX Every DOI name is also a Handle identifier and, as
such, consists of a prefix and a suffix separated by a forward slash
character ("/"), e.g.: 10.1000/292 The prefix ("10.1000" in the example
above) identifies the person or organization that has requested and
received the registration of the DOI name (the registrant). It consists
of one or more segments separated by the full-stop character (".")
Currently, all DOI names start with the segment "10". The suffix ("292"
in the example above) is chosen by the registrant identified by the
prefix and is unique for a given prefix. It is an arbitrary string. This
can be specific to the registrant or incorporate an identifier generated
from, or based on, another system. See Chapter 3 for detailed
information on the syntax of DOI names. No definitive information can be
inferred about a referent from a DOI name alone. In particular, the
inclusion in a DOI name of any registrant code allocated to a specific
registrant does not provide evidence of the ownership of rights or
current management responsibility of any intellectual property in the
referent. Such information may be asserted in the associated metadata.
DOI names can be represented in a number of ways depending on the
context, including as URLs, URNs and URIs, as described in 3.5.

DOI HANDBOOK 11 2.4 STRUCTURED SEMANTICS BASED ON STRICT PRINCIPLES The
metadata describing an entity is provided by the registrants of the DOI
names to the Registration Agency (RA) who provides the registration
service. The aim is to achieve metadata interoperability, the automated
integration of metadata in the DOI System, and to distinguish DOI
records from other records. This section introduces the principles of
the DOI System metadata model. For more information, see Chapter 4.

2.4.1 PRINCIPLES OF THE METADATA MODEL The principles of the metadata
model are: • unique identification Every entity must be uniquely defined
within an identified namespace. • functional granularity It should be
possible to identify an entity whenever it needs to be distinguished. •
designated authority The creator of the metadata must be identified
without doubts about its identity. • application independence The
metadata schema should be independent of the technology used. •
appropriate access Everyone must have access to the metadata needed. The
consequence of this principle is that ot all metadata must be accessible
to everyone. In certain circumstances, some metadata would be
inaccessible for certain users.

2.4.2 STANDARD METADATA DECLARATION A standard metadata declaration must
be made for every entity identified with a DOI name according to the
following principles: • The declaration must contain a minimum set of
mandatory metadata called System Metadata. This metadata is designed to
be as limited in scope as possible, and it is applicable to any entity
identifiable by the DOI System. • Allowed values for Referent types and
sub-types are managed with over-sight of the DOI Foundation • Basic
Metadata sufficient to define what the referent is must be specified per
sub-type • Where more than one registration agency assigns DOIs to a
referent sub-type, Basic Metadata interoperability will be improved with
agreement on data elements or a mapping between them • RAs can allow
additional metadata to be declared and managed • All declared System
Metadata is which specifies all data elements and allowed values.

The metadata schema is extensible to whatever level of detail and
granularity is required, and is neutral (it is independent of any
business and any implementation technology). It allows the RAs to use
any metadata scheme, yet still ensures semantic equivalence with DOI
names assigned by others: • Terms can be added to System Metadata model
at the request of any RA, however, where this concerns a referent
sub-type with an agreed interoperable approach this is coordinated by
the DOI Foundation. • The DOI System Metadata model provides the
mappings to support metadata integration and transformations required
for data exchange between RAs. The figure below illustrates the metadata
creation flow. The registrant of a referent provides the metadata
describing the referent. The RA's metadata service creates the
corresponding metadata declaration(s) according to the metadata schemas
and assigns them to the respective DOI name.

DOI HANDBOOK 12 Figure 4 Metadata declaration For more information, see
Chapter 4.

2.5 BASIC RESOLUTION SERVICES PROVIDED BY THE DOI SYSTEM The basic
resolution function of the DOI System consists in redirecting a user to
a web resource on resolution of a DOI name. The end-user can perform
this basic resolution request from any standard web browser.

2.5.1 DIRECT REDIRECTION TO A WEB RESOURCE WITH THE DOI PROXY The most
common resolution function of a DOI name returns a single web address
(or URL for Uniform Resource Locator) to which the user is redirected as
illustrated below. This is done by using the HTTPS Proxy Server of the
DOI System (https://doi.org). With the DOI Proxy, users can resolve DOI
names from any standard web browser by using the URL syntax (A proxy
server is a web server that understands the Handle System protocol,
thereby acting as a gateway between the Handle System and HTTPS.). For
example, the resolution of the DOI name "10.10.123/456" would be done
from the address "https://doi.org/10.123/456". That makes the DOI
resolution service extremely easy to use.

DOI HANDBOOK 13 Figure 5 Direct redirection to a web resource

2.5.2 ADDITIONAL RESOLUTION SERVICES INCLUDED IN THE DOI SYSTEM The
following resolution services are included in the DOI System in addition
to the main DOI resolution service: • shortDOI The shortDOI Service
creates shortened DOI names, as aliases for existing DOI names, which
are often very long strings. Applications which resolve DOI names will
treat a short DOI identically to the original. For more information, see
5.5. • Which RA? This service returns the name of the DOI Registration
Agency (RA) responsible for a specific DOI name, or group of DOI names.
For more information, see 5.6.

2.6 VALUE-ADDED SERVICES A REGISTRATION AGENCY CAN BUILD ON THE DOI
SYSTEM Registration Agencies can provide various added-value services by
using the multiple resolution request supported by the DOI resolution
service. In contrast to the single resolution which can only return a
single web address (URL) element, the multiple resolution allows making
use of any useful information in any form

DOI HANDBOOK 14 returned in the DOI record. While the multiple
resolution is typically used to acquire multiple URLs, it is flexible
enough to provide information for many other applications. This section
describes some examples of these added-value services.

2.6.1 MANAGEMENT OF A REFERENT WITH SEVERAL INSTANCES In case a referent
is linked to several web resources - for example, if an article is
available in PDF and in HTML versions then two web addresses (URLs) are
provided - then a resource selection mechanism must be implemented by
the Registration Agency (RA). It may be: • a manual selection When the
user requests the referent's DOI name from the RA's application, the
application generates a menu of options from which the user performs a
manual choice. • an automated selection The URL to which the user is
redirected is automatically selected among a list of provided addresses
according to predefined rules that may be based on parameters depending
on the user (for example, the user's geographic location which would be
determined through their IP address). The menu options or the
redirection rules are retrieved from the DOI record. In particular,
redirection rules can be defined through a redirection graph element
containing XML code which can be interpreted by the DOI resolution
service as illustrated below.

Figure 6 Management of a referent with several instances

2.6.2 DYNAMIC BUILDING OF A WEB PAGE ENRICHED WITH METADATA On request
of a user for a referent, Registration Agencies (RA) can dynamically
build a web page displaying the metadata assigned to the respective DOI
name. The metadata is provided by the RA's metadata service responsible
for the respective DOI name. The address of this metadata service can be
retrieved from the DOI record. The figure below illustrates an
application where each product of a building structure is identified
through a DOI name which is printed on the physical product in the form
of a QR code. When a user scans the QR code, they are redirected to a
product landing page where they can quickly find all the most up-to-date
information on a product.

DOI HANDBOOK 15 Figure 7 Dynamic building of a web page enriched with
metadata

2.7 BUSINESS AND ORGANIZATIONAL MODEL OF THE DOI SYSTEM The DOI System
is deployed via Registration Agencies (RAs) who are empowered to assign
DOI names for a community under the governance of the DOI Foundation.

2.7.1 FEDERATION OF REGISTRATION AGENCIES (RA) The DOI System is
implemented through a federation of Registration Agencies (RA) who
provide services to users (registrants): • Registration Agencies must
comply with the policies and technical standards established by the DOI
Foundation, but are free to develop their own business model for running
their businesses. • Users can join a service offered by an RA by
registering material with one of them, or developing a community to
build an RA. • Registrants ensure appropriate content management of
their own material (maintenance of URLs and data), either directly or by
contract (for example, with the RA).

2.7.2 FREE RESOLUTION SERVICE The DOI Foundation maintains a DOI Proxy
that can resolve all DOI names. Users can be any person or machine that
wants to resolve a DOI. They do not have to be members of the DOI
Foundation and may use the DOI Proxy as often as they like. DOIs are,
and will always be, free to resolve.

DOI HANDBOOK 16 2.7.3 GOVERNANCE ROLE OF THE DOI FOUNDATION The DOI
Foundation is the governance body of the DOI System: • It safeguards
(owns or licenses on behalf of registrants) all intellectual property
rights relating to the DOI System. • It works with RAs and using the
underlying technical standards of the DOI System components to ensure
that any improvements made to the system (including creation,
maintenance, registration, resolution and policymaking of DOI names) are
available to any DOI name registrant, and that no third-party licenses
might reasonably be required to practice the DOI name standard. • It
provides agreed standards of governance, scope, and policy, and also a
technical infrastructure (resolution mechanism, proxy servers, mirrors,
back-up) and a social infrastructure (persistence commitments, fall-back
procedures, cost-recovery (on a self-sustaining model), and shared use
of the system).

2.7.4 DOI NAMESPACE ALLOCATION APPROACH The DOI namespace allocation
approach is as follows: • The DOI Foundation allocates one or several
prefixes derived from its top-level prefix (10) to an organization that
wishes to register DOI names (a Registration Agency (RA)). • The RA
registers DOI names under their allocated prefix(es). If the RA
allocates a separate prefix to each of their customers (registrants)
then the combination of a prefix for the registrant and suffix provided
by the registrant (which is unique within their prefix) avoids any
necessity for the centralized allocation of DOI names. The following
figure illustrates the DOI namespace allocation approach.

DOI HANDBOOK 17 Figure 8 DOI namespace allocation approach

2.8 STANDARDIZATION OF THE DOI SYSTEM

2.8.1 ISO 26324 The DOI System has been standardized by the
International Organization for Standardization (ISO) as ISO 26324,
Digital Object Identifier System ISO 26324 specifies the syntax,
description and resolution functional components of the DOI System, and
defines a single entity (the "Registration Authority") that is
responsible for the implementation and operation of the DOI System,
including allocating DOI names -- see 2.1.3 for additional details. Per
agreement with ISO, the DOI Foundation is the sole Registration
Authority for ISO 26324, i.e., no other organization can manage the
identifiers that conform to ISO 26234 ISO 26324 is managed by the TC
46/SC 9 (Identification and documentation) committee, of which the DOI
Foundation is an active member. Norman Paskin wrote a history/case study
of DOI standardization, "The Digital Object Identifier: From Ad Hoc to
National to International".

DOI HANDBOOK 18 2.8.2 CONFORMANCE WITH RELEVANT EXTERNAL STANDARDS The
DOI System has also been developed to ensure conformance with relevant
generic external formal standards, including URL. It implements the
Handle System which conforms with the DO-IRP protocol: see Digital
Object Identifier Resolution Protocol (DO-IRP) Specification The DOI
Foundation supports the FAIR principles which provide guidelines to
improve Findability, Accessibility, Interoperability and Reuse of
digital assets. The FAIR principles emphasize machine-actionability (the
capacity of computational systems to find, access, interoperate, and
reuse data with none or minimal human intervention) because humans
increasingly rely on computational support to deal with data as a result
of the increase in volume, complexity, and creation speed of data. Note
that FAIR principles may not be relevant to some use cases of the DOI
System.

2.9 PERSISTENCE AS A DESIGN FEATURE OF THE DOI SYSTEM Persistence of DOI
information is a key aim of the DOI System, and is guaranteed by the DOI
social infrastructure through policies and agreements, and assisted by
technology. Table 1 Persistence considerations in the DOI System
Persistence aspect Solution in the DOI System

Persistence of the access to data in case the referent Through the DOI
name resolution concept, DOI location or ownership changes or in case
the referent names resolve to information (DOI record) which may is no
longer available change over time (URL, object ownership, etc.) while
the mapping of the DOI name to the entity persists. It is the
responsibility of the registrant to maintain the data of the DOI record.
In case the object identified by a DOI name is no longer available, the
DOI name registrant can at minimum have the DOI name resolve to a
response screen indicating that the object is no longer available.

Persistence of the access to data in case a RA membership imposes
certain obligations on an Registration Agency (RA) is defaulting RA to
ensure transfer of appropriate records and enable continuity of DOI
resolution in case the RA is defaulting. Membership of the DOI
Foundation is predicated on the assumption that communities wish to work
together to ensure long term persistence, beyond the interests of their
own current applications. Should this assumption be false, the DOI
agreements provide a fall-back position enabling persistence of
resolution of the assigned DOI names. Note: Added-value services
available through DOI resolution which are provided by a Registration
DOI HANDBOOK 19  Persistence aspect Solution in the DOI System

                                                          Agency cannot be guaranteed to be maintained by
                                                          the DOI Foundation in the event of the Registration
                                                          Agency ceasing to exist. Such services may require
                                                          additional material (for example, access to metadata
                                                          lookup or workflow procedures). However, the DOI
                                                          Foundation will make best efforts to transfer such
                                                          services to another agency, or maintain such
                                                          services itself, or encourage that services are
                                                          transferred to a third party able to provide continuity
                                                          where required. The aim will be to provide the least
                                                          disturbance to the community of users of those DOI
                                                          records.

Persistence of the DOI System in case the DOI In the event of the DOI
Foundation ceasing to exist, Foundation ceases to exist, or the current
technical agreements are in place to transfer the system to
implementation is unable to sustain its activities other parties. The
DOI Foundation's agreement with technical support partners allows for
reversion of all DOI System data, licenses, rights etc. to the DOI
Foundation in the unlikely event of the current technical implementation
closing or being unable to sustain its activities.

Persistence of the technical infrastructure technology The DOI system
uses a globally distributed multiple site network of servers and service
sites overlain on the Handle System, which itself has similar
distributed sites. These sites are at individual RA member locations,
professional co-location hosting sites, and virtual (cloud computing)
facilities, with resources to ensure 24x7 cover, mirroring machines to
ensure against power outages, etc. The DOI Foundation also ensures that
the doi.org domain is part of the persistent technical infrastructure,
including mirroring and load balancing to ensure optimal availability
for HTTPS requests to the DOI Proxy. The Handle System is governed by
the DONA Foundation which is committed to ensure the system continuity.
The Handle System is an open standard, so anyone can build/use a Handle
service. Both source code and APIs are public.

2.10 BENEFITS OF THE DOI SYSTEM The following paragraphs describe some
of the benefits made possible by the DOI System.

DOI HANDBOOK 20 2.10.1 IMPROVED CONTENT MANAGEMENT AND DISCOVERY
Benefits of implementing the DOI system include facilitating internal
content management and enabling faster, more scalable product
development, by delivering four key advantages in making it easier and
cheaper to: • know what you have Users are able to look at catalogues of
content available throughout the enterprise. • find what you want Users
are able to search and browse for content to be used or re-purposed. •
know where it exists Users are able to see where the item exists within
the organization. • be able to get it Users and production tools are
able to retrieve information about the referent (e.g. the content itself
for an online resource).

2.10.2 SOLUTION TO THE BROKEN LINK (PERSISTENCE) The DOI System provides
the means for a solution to the famous web issue of "http 404 not found"
(broken link). The problem is that a URL (Unified Resource Locator) is
both an identifier and a locator for a resource on the Internet. The
specific content of the URL that is its identifier is also the string
that can be resolved into a location. This has the consequence that when
a resource is moved from one service to another, from a server to
another, or from a company to another, it will get a new URL that
identifies the service, the server or the company that hosts it. Its old
URL will most likely stop working and any previously made references to
that resource using the old URL will no longer work. With the DOI
System, the identifier is persistent, whereas the metadata to which it
resolves can change over time, in particular, the URL can be updated.
For more information, see Chapter 3.

2.10.3 IDENTIFIER INTEROPERABILITY THROUGH A POWERFUL METADATA MODEL
Resources of interest in digital networks originate from a wide variety
of sources, and may carry identifiers from different established public
schemes, official standards, de facto schemes, or private cataloguing
numbering. A key step in facilitating preservation, re-use and exchange
of information is to enable users to re-use these identifiers (and their
associated data) across different applications. For example, where
several Registry Agencies (RA) are issuing DOI names to journal articles
from different publishers, it is likely that some RAs and publishers
will want their DOI names to be included in journal-related services
supported by other RAs. In a similar way, many RAs will want DOI names
issued by other RAs to be available for inclusion in services they
themselves are providing. Such interoperability is one of the principal
benefits of the DOI System. To achieve identifier interoperability in
the DOI System, tools and policies are used: see 1.4.

2.10.4 COMPATIBILITY WITH OTHER IDENTIFIER SYSTEMS The DOI System is not
meant to replace existing identifier systems. Instead, it is designed
for interoperability; that is to use, or work with, existing identifier
and metadata schemes. The DOI System explicitly recognizes other
schemes. The ISO DOI specification (ISO 26324) sets out the
specifications for recognizing existing schemes. At minimum, the System
Metadata must record the fact that another registry identifier exists.
Additional optional steps are possible, including: • a consistent way of
including the other scheme in the DOI syntax • a business relationship
to facilitate this, by collaboration between the DOI Foundation and the
relevant registry Where such collaboration is agreed, new potential may
be unlocked: the ISBN-A application is an DOI HANDBOOK 21  example of
the linkage of DOI names to an existing registry. For more information,
see DOI System and the ISBN System.

2.10.5 SERVICE FLEXIBILITY AND EXTENSIBILITY The DOI System supports any
type of physical, digital or abstract entities, and of hierarchies and
relationships between entities. Through its scalable architecture, the
DOI System is able to handle very large volumes of registrations and
resolutions of DOI names. In fact, the DOI System is made up of Local
Handle Services (LHS) of the Handle System (an LHS manages the DOI names
under one or several prefixes): each LHS may be replicated into multiple
service sites and each service site may consist of multiple computers
(servers). It means that service requests targeted at any LHS can be
distributed into different service sites, and into different servers
within any service site.

2.10.6 PROTECTED AND TRUSTED INFORMATION The Handle System - which is
used for identification and resolution of DOI names - provides client
and server authentication, data confidentiality and integrity, and
non-repudiation based on Public Key Infrastructure (PKI): • Any
exchanged information between a client and a server of the Handle System
can be encrypted using a session key. • To ensure non-repudiation,
clients may request digitally signed responses from any server. • User
access control is supported at DOI record and record element levels.
Resolution requests for confidential data, as well as any administration
requests (for example, creating or modifying a DOI record) require
authentication of the user for proper authorization. • The integrity of
a DOI record's data is ensured by signing the DOI record. The digital
signature is stored in the DOI record itself and can be validated
through a chain of trust.

2.10.7 INFORMATION TRACEABILITY Traceability is not provided by the DOI
System but can be made available through the Digital Object Architecture
(DOA) on which the Handle System is based (more precisely, through the
DOA's Digital Object Interface Protocol (DOIP)). Different actors may
interact with the Digital Object (DO) (which represents the referent)
throughout its life cycle. Each action is tracked in the DO itself and
this information can be processed for various applications. For example,
in the movie industry, this allows providing digital revenue reporting
as well as detailed consumption metrics for individual assets.

2.11 APPLICATION EXAMPLES OF THE DOI SYSTEM Many millions of DOI names
have been assigned to date, through a growing federation of Registration
Agencies worldwide. For example: • Crossref manages DOI names for the
scientific publishing industry. Its application is used by publishers
and societies to enable cross-citation of scholarly publications. •
DataCite provides DOI name services for referencing and sharing research
out-puts and resources, primarily research data sets, text and samples.
• The Entertainment ID Registry (EIDR) provides identifiers and
associated metadata that are used in the commercial film and video
industry, from post-production through broadcast, digital distribution,
and reporting.

DOI HANDBOOK 22 • The British Standards Institution (BSI) Identify uses
DOI names in building construction projects to identify the products
used in the buildings (interior furnishing, lighting, etc.) and manage
their supply chain information. For more information, see Registration
Agencies - Areas of Coverage.

DOI HANDBOOK 23 Chapter 2

DOI SYSTEM GOVERNANCE AND PARTICIPATION

This chapter describes the role and functions of the DOI Foundation and
of Registration Agencies within the DOI System. It also summarizes the
policies governing the DOI System and explains the policy formulation
process.

In This Chapter 3.1 DOI System Governance Body: The DOI Foundation
.................... 25 3.2 DOI System Participants: Registration
Agencies and Registrants
........................................................................................................................
30 3.3 DOI System Governing Policies
................................................. 33

DOI HANDBOOK 24 3.1 DOI SYSTEM GOVERNANCE BODY: THE DOI FOUNDATION This
section describes the status, roles, membership and governance of the
DOI Foundation.

3.1.1 STATUS OF THE DOI FOUNDATION The DOI Foundation is a non-stock
membership corporation organized and existing under and by virtue of the
General Corporation Law of the State of Delaware, USA, registered on 10
October 1997, registration number 2807134 8100. The DOI Foundation's
corporate registered address is via CT Corporation: The Corporation
Trust Company, Corporation Trust Center, 1209 Orange Street, Wilmington
DE 19801, USA. The Foundation is controlled by a Board elected by the
members of the Foundation. The Corporation is a not-for-profit
organization, it means prohibited from activities not permitted to be
carried on by a corporation exempt from US federal income tax under
Section 501(c)(6) of the Internal Revenue Code of 1986 et seq. The
operational address of the Foundation is: The DOI Foundation, c/o
EDitEUR Limited, United House, North Road, London N7 9DP, UK. Costs
incurred by the DOI Foundation are recouped from the operation of the
system via a self-funding business model. The implementation of the DOI
System adds value, but necessarily incurs some resource costs in data
management, infrastructure provision, and governance, all of which
contribute to persistence. Persistence is a function of organizations,
not technology. A Managing Agent is contracted by the DOI Foundation,
who represents the DOI Foundation worldwide, and is responsible for the
implementation of policies and management of all aspects of the affairs
of the DOI Foundation. Functions such as technical operations, legal and
financial services are outsourced.

3.1.2 OVERVIEW OF THE DOI FOUNDATION ROLES The DOI Foundation is the DOI
System registration authority and maintenance agency and the central
body which governs the DOI System. It is the common management and
co-ordination body for DOI Registration Agencies. It also manages those
aspects of the DOI System that are put through external standardization
procedures, as well as those aspects of the DOI System that are dealt
with through internal policies and procedures. Responsibilities of the
registration authority include: • to promote the proper use of the DOI
System (and ISO 26324, the ISO specification) • to maintain the DOI
System technical infrastructure and data in accordance with the needs of
the users • to establish guidelines regarding allocation, registration,
maintenance and dis-semination of DOI names • to continuously adapt the
DOI Handbook and guidelines to meet the needs of the market • to respond
to enquiries and information requests related to ISO 26324 in a timely
manner • to establish due diligence and quality assurance procedures of
the DOI System

3.1.3 ISO 26324 REGISTRATION AUTHORITY The DOI Foundation is the ISO
26324 Registration Authority, governed by an agreement between ISO and
the DOI Foundation. The responsibilities of the ISO 26324 Registration
Authority are stipulated in Annex C of the standard. ISO 26324 specifies
the duties of the Registration Authority: services to be provided and
technical duties. SERVICES TO BE PROVIDED BY THE REGISTRATION AUTHORITY
The ISO 26324 Registration Authority shall provide the following
services:

DOI HANDBOOK 25 • promote, coordinate and supervise the DOI System in
compliance with the specifications of the International Standard •
supply technology and infrastructure for resolution, metadata and
registration functionality according to the specifications of the
International Standard and ensure that any changes in selected
technology will be compatible with earlier DOI applications • allocate
unique DOI prefixes to registrants and maintain an accurate register of
the DOI prefixes that have been assigned, ensuring so far as possible
uniqueness with respect to other identification schemes with a similar
syntax • secure the maintenance of DOI names and associated DOI
resolution records through the maintenance of a single logical directory
of all registered DOI names, the DOI directory • implement policies and
procedures governing the process of DOI registration, including rules to
aid persistence of DOI names and interoperability within networks of DOI
users • develop, maintain and make documentation available for users of
the DOI system, including the provision of a handbook for registrants
which shall specify implementation details in conformance with the
International Standard • review relevant technology developments and
maintain current information on appropriate syntax character encoding,
resolution software implementations, etc. • where multiple DOI names are
assigned to the same referent (e.g., through assignment of DOI names by
two different registrants, provide a unifying record for that referent
CONDITIONS FOR REGISTRATION The ISO 26324 Registration Authority shall
ensure that each registrant conforms with the following conditions. •
the DOI suffix assigned within their DOI prefix is unique, thereby
ensuring that each DOI name is unique within the DOI system • each
referent registered is assigned only one DOI name. Where multiple DOI
names are inadvertently assigned to the same referent, provide a
unifying record for that referent • each DOI name assigned is registered
with system metadata following the specifications established by the ISO
26324 Registration Authority and any further rules established for its
internal management TECHNICAL DUTIES OF THE REGISTRATION AUTHORITY The
ISO 26324 Registration Authority shall provide the following technical
services by means of a handbook: • maintain a list of approved
resolution services (such as https://doi.org/) that resolve DOI names •
provide current information on appropriate encoding of characters •
provide current information on resolution technology • maintain a list
of representations used in other schemes • provide information on common
encodings • specify, if required, more constrained rules for the
assignment of DOI names to objects for services which make use of the
DOI System. Where specified, these rules shall be compatible with the
overall DOI system specification and shall not form part of the
International Standard. • Provide granularity rules that specify under
which circumstances changes to a referent or its metadata, including its
ownership, generally requires the assign-ment of a new DOI name •
publish rules to aid persistence of identification (for example,
requirements for maintenance of records, default resolution services) •
provide output system metadata to support the use of the DOI system •
prevent duplication of a DOI name once registered • make publicly
available the system metadata associated with each referent

DOI HANDBOOK 26 3.1.4 REPRESENTATION TO STRATEGIC ORGANIZATIONS A key
role of the DOI Foundation is representation to organizations which are
of strategic importance in the implementation of the DOI System. This
includes: • participation in governance and continuity activities of the
Handle System whose central body is the DONA Foundation. In addition,
the DOI Foundation has contractual agreements for provision and
persistence of the Handle System with the DOI technical support service
provider (who is currently CNRI) • maintenance of formal and informal
alliances and liaisons with several other organizations. A significant
element of the work of the DOI Foundation lies in tracking standards
developments in related areas, understanding their significance to the
context within which the DOI System operates, and establishing working
relationships with the responsible organizations and projects to ensure
that appropriate co- operation is fostered to mutual benefit and that
parallel develop-ments do not remain in ignorance of one another. • role
as the formal Registration Authority of the ISO/IEC MPEG21 Rights Data
Dictionary This standard is not a requirement for DOI System use. For
further information, send questions to info@doi.org.

3.1.5 DOI FOUNDATION MEMBERSHIP The activities of the foundation are
controlled by its members, operating under a legal Charter and formal
By- laws. Membership is open to all organizations with an interest in
digital network publishing, content distribution, rights management, and
related enabling technologies. MEMBERSHIP OBLIGATIONS By participating
in membership of the DOI Foundation, members agree to: • support the
goals of the DOI Foundation, which ensure that the DOI System is an
internationally adopted standard for digital object identification •
participate in the activities of the DOI Foundation • comply with the
Foundation's By laws, Agreements and Policies as these may be updated
from time to time • restrict access to the password-controlled portions
of the Foundation's web site to members of the Foundation • adopt the
DOI brand identity The DOI Foundation provides members with the current
identity information and with marketing materials • add the DOI
Foundation to the circulation of all their press releases and news
announcements, and to notify the Foundation of forthcoming relevant
events and activities Selected news about members' DOI activities may be
carried on the DOI News page, with a link to the original announcement.
MEMBERSHIP CLASSES There are four classes of membership: • General
Membership This membership is offered to any organization supporting the
development of the DOI System that is not a Registration Agency. It is
subject to a signed agreement. General membership is a pre-requisite for
any organization applying to become a Registration Agency. If a General
Member subsequently is appointed as a Registration Agency, their
membership transfers from the General to the RA category. • Registration
Agency Membership This membership is only available to organizations who
have successfully under-gone the process of becoming a Registration
Agency (RA) (see 2.2.5). The primary role of RAs is to provide services
and applications to registrants by allocating DOI prefixes, registering
DOI names and providing the necessary in-frastructure to allow
registrants to declare and maintain System Metadata and DOI records. For
more information about RAs, see 2.2.

DOI HANDBOOK 27 • Charter Membership This membership was initially
established for founding the DOI Foundation and is only offered to
organizations whose main activities are in the creation or production
and dissemination of intellectual property. The DOI Board reserves the
right to determine eligibility for the Charter membership category. •
Affiliate Membership This membership is restricted to professional
associations who have one or more of their current members in current
membership of the DOI Foundation. Organizations outside this scope may
be invited or admitted at the Board's sole discretion. Affiliate
membership does not carry voting rights, and Affiliate members are not
eligible for Board membership. Registration Agencies are not eligible
for this category of membership. General, Registration Agency and
Charter members are entitled to vote in annual DOI Foundation's
elections within their own category of membership (There are no
differences in member rights and benefits between Charter and General.).
Affili-ate membership does not carry voting rights. More information is
available on the membership classes on the DOI web site. MEMBERSHIP FEES
This paragraph describes general statements about DOI Foundation
membership fees. The following rules apply: • Membership fall due
annually on the anniversary of joining. • Membership reduction may be
applied as follows: • General membership fee may be reduced at the sole
discretion of the DOI Board. • Registration Agency membership fee is
included as part of operational fees, allocated annually on a
cost-sharing model (see 2.2.6). • Criteria which will be considered for
fee reduction include, in particular, any of the following: •
organizations with a significant role in the creation or ongoing support
of the DOI Foundation • not-for-profit organizations, depending on their
annual revenue • for-profit organizations, depending on their annual
revenue and other criteria • If a General member subsequently is
appointed as a Registration Agency (RA), their membership transfers from
the General to the RA category, and any unexpired portion of the
previous General membership fee is credited to their RA mem-bership dues
NOTE: In general, it is likely that the cost of fees will be deductible
as a business expense of the joining entity. The detailed question of
deductibility is, however, a matter for the tax advisors of the entity
that is joining, and it is not governed by DOI Foundation's status as a
not-for-profit entity. MEMBER STRATEGY MEETINGS Strategy meetings of the
DOI Foundation members are held at least once a year, and usually one in
mid-year and one at the end of the year, and are open to all members and
non-member guests (by invitation only). Members are advised of
forthcoming meetings by email. DOI REPRESENTATIVE OF A MEMBER
ORGANIZATION Each member organization of the DOI Foundation must provide
one named DOI representative, who will be responsible for the DOI
matters. In particular, the DOI representative will represent the
organization at all Board meetings and in voting issues. Members must
ensure that the DOI Foundation is kept informed of any representative
changes. Should the individual leave the member organization, or step
down from the representation role, the organization will name a
replacement. Additional persons from the member organization may
participate in all DOI activities. TRIAL PREFIX On joining the DOI
Foundation, a unique DOI prefix is available for experimental purposes
for each member. The number of DOI names allocated with this
experi-mental prefix will be subject to review and may be limited at the
discretion of the DOI Foundation. If further DOI prefixes are required
for non-experimental purposes, DOI HANDBOOK 28 members must work with
one of the Registration Agency members. Trial prefix use is particularly
intended for those members wishing to develop applications and move to
later Registration Agency status. Contact the DOI technical support
service provider (doi-admin@doi.org) to request one, and discuss
possible usage.

3.1.6 DOI FOUNDATION GOVERNANCE The DOI Foundation is governed by its
members, through an elected Board. BOARD OF DIRECTORS The Board is
responsible for all aspects of management of the DOI System, including
policy formulation and standards maintenance. The Board consists of: •
Board officers: a Chair, Vice Chair, and Treasurer, each elected from
the Board • Board members Members of the DOI Foundation become Board
members according to the following rules: • All Charter members are
automatically members of the Board. • All Registration Agency (RA)
members are automatically members of the Board after one full year of RA
membership • o General members are represented by one seat on the Board
held for a three-year term, nominated from amongst the existing General
members. Procedures for election in the event of more than one
nomination are defined in the By-Laws. • Affiliate Members are not
represented on the Board. The Board reviews the number and distribution
of Board seats from time to time. NOTE The members of the Board are not
remunerated for their services to the DOI Foundation. EXECUTIVE
COMMITTEE The Executive Committee is a subcommittee of the Board,
elected by the Board, consisting of not fewer than three Directors and
chaired by the Chairman of the Board. It may meet between Board meetings
to deal with matters not requiring a meeting of the full Board, or
requiring urgent discussion. In practice, the Executive Committee
normally consists of the Chair, Vice Chair and Treasurer. MANAGING AGENT
The Board of Directors of the DOI Foundation appoints a Managing Agent
responsible for managing the DOI Foundation and carrying out policy
formulated by the Foundation. BOARD MEETINGS The Board meets regularly.
Issues which any member feels should be considered by the Board should
first be brought to the attention of the Managing Agent or a Board
member. Board meetings are open to all members who may attend as
ob-servers and participate but not vote, except for designated closed
Executive Sessions. The DOI representative of each organization will
represent the organization at all Board meetings and in voting issues.
Substitution of another individual from the organization at Board
meetings is possible by advance agreement of the Chair of the Board.

DOI HANDBOOK 29 3.2 DOI SYSTEM PARTICIPANTS: REGISTRATION AGENCIES AND
REGISTRANTS A Registration Agency (RA) (formally called Registration
Agency Member) can be considered as a module of the DOI System, serving
a constituency. New RAs can be added at any time, thereby allowing
modular growth of the system by adding new communities of users and
providing tailored services for them. A registrant is a person or
organization who has requested and received the registration of a
particular DOI name. This section explains the role and function of
Registration Agencies in the DOI Sys-tem, including operational and
technical requirements and policies. A list of cur-rent Registration
Agencies and their areas of coverage is available on the DOI web site.

3.2.1 ROLES OF A REGISTRATION AGENCY A Registration Agency (RA) provides
services to one or several communities of us-ers. A community is loosely
defined, but could be any group of parties sharing a common application
or interest, under any organizational structures (public, pri-vate
sector, not-for profit, regulator, etc). The services an RA provides to
their users include: • allocating prefixes • registering DOI names and
providing the necessary infrastructure to allow regis-trants to declare
and maintain System Metadata and DOI record (in other words, use of the
DOI System) • · services not directly involving the DOI System which add
value, for example: management of a database of related data with
facilities for look-up from metadata to DOI name The role of an RA could
also encompass any of the following activities: • providing information
and advice to the community • providing applications, services,
marketing, outreach, business cases etc. to introduce the DOI System to
the community • designing and implementing specific operational
processes, for example: quality control of input data and output data •
integrating the community into other DOI related activities and services

3.2.2 BUSINESS MODEL FOR REGISTRATION AGENCIES Registration Agencies
(RA) must comply with the policies and technical standards established
by the DOI Foundation, but are free to develop their own business model
for running their businesses. There is no appropriate "one size fits
all" model. RAs may be of any form (commercial, governmental, or not for
profit). Examples of the functions of an organization which might become
an RA include, but are not limited to: • An organization is running a
registry (of identifiers and related data) and wishes to add DOI
functionality and services to its existing services. • An existing
aggregator of information wishes to use DOIs to improve their services
and add new features. • A new initiative is launched in a defined sector
to meet specific needs or solve a problem, for example, an industry
collaboration or effort to solve a common problem (examples of these
including Crossref, DataCite and EIDR are amongst the most successful
existing RAs). • A start-up which has a business model suggesting a
novel DOI application might be fruitful: in view of the importance of
persistence, this is likely to require significant guarantees of
continuity planning.

DOI HANDBOOK 30 The costs of providing DOI registration may be included
in the services offered by an RA provision and not separately
distinguished from these. Examples of possible business models may
involve: • explicit charging based on the number of prefixes allocated
or the number of DOI names allocated • volume discounts, usage
discounts, stepped charges, or any mix of these • indirect charging
through inclusion of the basic registration functions in related value
added services • cross-subsidy from other sources

Operational costs of the system are borne directly or indirectly by the
registrants. The business model adopted by an individual RA is a matter
for the RA alone, pro-vided that it complies with the DOI Foundation's
policies. NOTE RAs may choose to provide other DOI System-related
services to registrants, without limitation as long as they conform with
DOI agreements and policies. These services may include any combination
of value added services in, for example, data, content or rights
management. RAs may also develop services that exploit the metadata that
they collect. RAs will typically register many thousands or millions of
DOI names, and have mul-tiple customers and services, thereby generating
economies of scale. RAs for smaller scale applications will probably not
be viable as stand- alone entities, though RAs may collaborate, for
example to share back-office services to improve viability. Communities
that cannot identify an acceptable RA should contact the DOI Foundation
to discuss how the DOI System might be used, and whether a new RA
application might be developed. NOTE Once a DOI name is assigned, anyone
may resolve that DOI name without charge. At least some information will
always be available on resolution.

3.2.3 SERVICE NON-EXCLUSIVITY AND COMPETITION MATTERS Exclusivity of DOI
name registration rights covering either a specific geographic territory
or a wide area of application in general (for example, audio) will not
normally be granted to any Registration Agency (RA). Exceptions are
possible, for ex-ample where the RA is mandated to operate as a service
for an existing closed community and will not offer their registration
services outside that community. DOI applications often overlap and in
the digital world any number of categorisations are possible, which
makes exclusive arrangements difficult. The only exception at present is
an implementation for the Publications Office of the EU, covering DOI
registration and management of official EU documents. In order to
maintain a persistent identifier, a DOI application normally provides
more value than simply registering a DOI, by offering an added value
service such as citation linking or metadata management. RAs operate as
independent businesses on the basis of these added-value services and
unique selling propositions they bring to offer to the market. In order
to provide some coherence of DOI services, applications to become an RA
are assessed in the context of likely business implications. Where there
is an overlap of the expected market or services of RAs, each will be
informed of the potential for overlap or competition and invited to
address the problem in such a way as to encourage uptake of the DOI
System as a whole whilst ensuring that legitimate business interests are
met.

3.2.4 RA AGREEMENT Registration Agencies (RA) enter into an agreement
with the DOI Foundation. A copy of this generic agreement is available
on the DOI web site (see RA Agreement). The RA agreement covers a number
of areas including: 1. Rights granted to the RA: • appointment as an RA
having the authority to assign DOI names as part of the DOI System using
the DOI prefix or prefixes that have been assigned to RA by the DOI
Foundation • nonexclusive right and license to use DOI trademarks DOI
HANDBOOK 31  • sub-licenses to exercise all rights in the implementation
technologies (such as the Handle System) required for the fulfillment of
RA's rights and obliga-tions as an RA under the DOI System 2.
Obligations of the RA: • remain a fully paid member of the DOI
Foundation, including adherence to all DOI agreements and policies •
provide registration services and infrastructure • adopt procedures to
assure quality • respect rights of other RAs 3. Obligations of the DOI
Foundation: • maintain the DOI System, infrastructure and documentation
• cooperate with RAs in setting policies and fees regarding RAs •
participate in ISO and other relevant standards-setting bodies 4. Rights
and intellectual property: • The DOI Foundation has the exclusive right
to appoint RAs and to be the Registration Authority of ISO 26324. •
Trademarks remain the property of DOI Foundation and are licensed to
RAs. • RAs may assert patent or other proprietary rights in the RA
services, but must comply with the DOI Patent and Trademark Policies. •
In the event of the DOI Foundation ceasing to be the Registration
Authority of ISO 26324, continuity must be ensured 5. Change procedures,
warranties, indemnities, and liability 6. Termination procedures,
including: • considerations in the event of an RA leaving the DOI
Foundation (for example, the transfer of registered DOI names to a
successor) • considerations in the event of the DOI Foundation being
unable to continue (for example, the orderly transition of the
responsibilities of the DOI Foundation to a successor)

3.2.5 PROCESS OF BECOMING A REGISTRATION AGENCY To become a Registration
Agency (RA), an organization must: 1. become a General Member of the DOI
Foundation Organizations interested in becoming a General Member of the
DOI Foundation with a view to developing an RA application are
encouraged to contact the DOI Foundation for an exploratory discussion.
See also the detailed DOI mem-bership information in 2.1.5. 2. have made
a successful application to the DOI Board to be appointed as an RA All
appointments as an RA are made at the discretion of the Board of the
Foun-dation. It is unlikely that an application simply to register DOI
names without of-fering additional services utilising these registered
DOI names will be accepta-ble or successful. Potential applicants are
strongly encouraged to review one or more of the existing RAs for
examples of services and operations. See also 2.2.2. 3. sign an RA
Agreement with the DOI Foundation: see 2.2.4

3.2.6 FEE STRUCTURE FOR REGISTRATION AGENCIES The DOI System is a
cost-recovery system. ISO Council resolution 17/2012 "approves that fees
can be charged on a cost-recovery basis by the DOI Foundation in the
operation of the Registration Authority for ISO 26324". The cost of
common DOI infrastructure (managed by the DOI Foundation on behalf of
all Registration Agencies) is met by a charge made to each Registration
Agency, whilst allowing each Registration Agency to adopt individual
commercial models incorporating DOI name registration for their
services.

DOI HANDBOOK 32 3.2.7 REGISTRANT ROLES AND DUTIES A registrant can be
any individual or organization who wishes to uniquely identify entities
using the DOI System. A registrant: • registers DOI names with a
Registration Agency (RA) If a registrant has multiple types of content
or application requirements, it may choose to use several RAs to provide
services. • ensures appropriate content management of their own material
(maintenance of URLs and data), either directly or by contract (for
example, with the RA) • has an agreed relationship as a customer or
client of an RA • does not need to be a member of the DOI Foundation

3.3 DOI SYSTEM GOVERNING POLICIES This section introduces the policies
governing the DOI System.

3.3.1 POLICY FORMULATION PROCESS Policies are developed within the
context of the DOI Foundation's By-laws and Charter. Within this scope,
formal agreements are in place between the DOI Foun-dation and its
partners. Individual policies are then defined consistent with these
agreements. Policy development takes place through discussion at regular
strategy and members meetings of the DOI Foundation, and sometimes
through working groups tasked with reviewing specific areas. All
proposed changes in the Core Specification or policies will be presented
initially to the RA Working Group (RAWG) for dis- cussion and approval
under such quorum and voting procedures as may be agreed by the RAWG
members. Changes approved by the RAWG must then be approved by the DOI
Foundation's Board.

3.3.2 LIST OF FORMAL DOI DOCUMENTS The table below lists the approved
policies and agreements governing the DOI System. NOTE Policies are
binding on all members of the DOI Foundation. Table 2 Formal DOI
Documents Formal document Description See

    Antitrust policy                  The DOI Foundation conducts             Antitrust Policy
                                      their     operations    in     strict
                                      compliance with the antitrust laws,
                                      regulations and guidelines of all
                                      jurisdictions where the Foundation
                                      conducts meetings, programs, or
                                      activities.


    Conflict of interest policy       This policy protects the interests      Conflict of interest policy
                                      of the DOI Foundation when it
                                      is contemplating entering into a

DOI HANDBOOK 33  Formal document Description See

                                  transaction or arrangement that
                                  might benefit the private interest
                                  of a Director or Officer of the
                                  Foundation.

Trademark policy Guidelines for use of Trademark Policy the trademarks
which the International DOI Foundation owns. DOI®, DOI\>®, DOI.ORG® and
shortDOI® are registered trademarks of the International DOI® Foundation

Patent policy Procedures relating to patent RA Patent Policy rights and
claims among Registration Agencies (RA): to enable the DOI System to be
available to all who want to use it on equal terms; to preserve and
protect the collective invest- ment in the DOI System and standard; and
to allow RAs to develop added-value services and features. The DOI
Foundation does not itself hold any patent rights in the DOI System.

Data policy This policy concerns Data policy confidentiality of data
such as us-age statistics and information about individual DOI name
resolution, for the DOI Foundation and the Registration Agencies.

RA collaboration policy General requirements and Collaboration policy
procedures for resolving conflicts between Registration Agencies and
encour-aging collaboration, to the benefit of the DOI commu-nity.

DOI Proxy implementation policy Requirements for support and Proxy
policies functionality of proxy servers by Registration Agencies,
including those run-ning instances of the DOI Proxy Server and their own
local proxies, and support for the DOI HANDBOOK 34  Formal document
Description See

                                   Default Proxy and the functionality
                                   of the Default Proxy.

Suspension and termination of an This document outlines RA Suspension
and Termination RA procedures for dealing with DOI Procedures names in
the event of suspension or termination of an RA.

General Member Agreement This agreement governs the terms General Member
Agreement and conditions under which a General Member of the DOI
Foundation agrees to participate in the DOI Foundation and use the DOI
System.

Registration Agency Agreement This agreement governs RA Agreement the
relationship between a Registration Agency (RA) and the DOI Foundation.
The RA agreement provides equal terms to each RA, unless specific
waivers or exceptions have been agreed to meet the needs of a specific
community.

ISO 26324: In-formation and ISO 26324 specifies the 1.8.1 documenta-tion
--- Digital object syntax, description and resolu- identifi-er system
tion functional components of the digital object identi-fier system, and
the general principles for the creation, registration and administration
of DOI names.

DOI HANDBOOK 35 Chapter 3

DOI NAMESPACE

This chapter defines the syntax for a DOI name and how DOI names can be
represented. It also explains the DOI name assignment principles and how
other identifier schemes can be integrated into the DOI system. For
information about the definition of prefix allocation and suffix naming
policies, see Chapter 8.

In This Chapter 4.1 Assignment Principles of the DOI Name
...................................... 37 4.2 Use of Unicode
.......................................................................
37 4.3 Syntax of the DOI Name
........................................................... 37 4.4
Representation Formats
........................................................... 39 4.5
Avoiding and Resolving Ambiguities when Presenting or Exchanging DOI
Names
...............................................................................................................
40 4.6 UTF-8 Serialization
.................................................................. 41
4.7 Percent-Encoding
.................................................................... 41
4.8 Integration of Other Identifier Schemes
....................................... 42

DOI HANDBOOK 36 4.1 ASSIGNMENT PRINCIPLES OF THE DOI NAME The following
principles for assigning DOI names apply: • A DOI name can be assigned
to any object whenever there is a functional need to distinguish it from
other objects. DOI names can be assigned at any desired degree of
precision and granularity that a Registration Agency deems to be
appropriate based on the needs of their community. • Each DOI name shall
specify one and only one referent in the DOI System. • The assignment of
a DOI name requires that the registrant provide metadata describing the
object to which the DOI name is being assigned. The metadata shall
describe the object to the degree that is necessary to distinguish it as
a separate entity within the DOI System. • No time limit for the
existence of a DOI name shall be assumed in any assignment (see 1.9). •
A DOI name shall not be used as a replacement for other ISO identifier
schemes.

NOTE While a referent can be specified by more than one DOI name, it is
usually recommended that each referent has only one DOI name. But
depending on the DOI application, there may be legitimate reasons to
assign multiple DOIs to the same referent.

4.2 USE OF UNICODE To support diverse applications worldwide, a DOI name
can use any Unicode character intended to be written, printed, or
otherwise displayed in a form that can be read by humans. With this
flexibility comes ambiguities when representing or exchanging DOI names.
For example: • the character "Á" (LATIN CAPITAL LETTER A WITH ACUTE) can
be encoded ei-ther on its own or as the character "A" (LATIN CAPITAL
LETTER A) followed by the combining character \## (COMBINING ACUTE
ACCENT); • multiple schemes (UTF-8, UTF-16 or UTF-32) can be used when
serializing a DOI name to bytes for interchange between machines; • the
glyph "Å" can either correspond to the ANGSTROM SIGN or the LATIN
CAPITAL LETTER A WITH RING ABOVE. To avoid these pitfalls, this document
specifies the syntax of a DOI name as a se-quence of Unicode code
points, where each code point is an integer between 0 and 0x10FFFF, and
the fundamental unit of encoding in Unicode.

4.3 SYNTAX OF THE DOI NAME The syntax of the DOI name is standardized as
part of ISO 26324.

4.3.1 GENERAL CHARACTERISTICS A DOI name consists of an ordered sequence
of code points of the Graphic type, as specified in the Unicode
Standard. The Graphic type includes all code points that are letter,
mark, number, punctuation, symbol and spaces. It excludes, for ex-ample,
control code points such as U+0009 HORIZONTAL TABULATION. The sequence
is further arranged in a DOI prefix and a DOI suffix separated by U+002F
SOLIDUS. EXAMPLE: In the DOI name "10.5594/SMPTE.ST2067-21.2020",
"10.5594" is the DOI prefix and "SMPTE.ST2067-21.2020" is the DOI suffix

DOI HANDBOOK 37 There is no defined limit on the length of the DOI name,
or of the DOI prefix or DOI suffix.

4.3.2 DOI PREFIX The DOI prefix is composed of a directory indicator
optionally followed by a registrant code. Where a registrant code is
present, the two components are separated by a U+002E FULL STOP. EXAMPLE
1: In the DOI name 10.5594/SMPTE.ST2067-21.2020, "10.5594" is the DOI
prefix, "10" is the directory indicator and "5594" is the registrant
code. The directory indicator consists of a sequence of digits between 0
and 9. It is usual-ly equal to "10" but other directory indicators may
be used in the future by the DOI Foundation. The registrant code
consists of sequences of digits between 0 and 9, separated by U+002E
FULL STOP. EXAMPLE 2: In the hypothetical "10.500.100" DOI prefix, the
directory indicator is "10" and the registrant code is "500.100". If the
directory indicator is equal to "10" then a registrant code is always
present.

4.3.3 DOI SUFFIX The DOI suffix is a sequence of Unicode code points
chosen by the registrant. The combination of DOI prefix and suffix is
unique, but the same DOI suffix can be used with different DOI prefixes.
The DOI suffix can be a sequential number, or it might incorporate an
identifier generated from or based on another system used by the
registrant (for example, ISAN, ISBN, ISRC, ISSN, ISTC, ISNI; in such
cases, a preferred construction for such a suffix can be specified, as
in Example 2). See also 8.3. EXAMPLES • Example 1 10.1000/123456: DOI
name with the DOI prefix "10.1000" and the DOI suffix "123456" • Example
2 10.1038/issn.1476-4687: DOI suffix using an ISSN To construct a DOI
suffix using an ISSN, precede the ISSN (including the hyphen) with the
lowercase letters "issn" and a period, as in this hypothetical example
of a DOI name for the electronic version of the scientific journal
Nature.

4.3.4 CASE INSENSITIVITY OF THE DOI NAME When comparing two DOI names
for equivalence, no normalization, as defined in ISO/IEC 10646, is
performed and the DOI names are equivalent if, and only if, their code
point sequences are identical, except that a code point in the range
U+0041..U+005A (corresponding to LATIN CAPITAL LETTER A to LATIN CAPITAL
LETTER Z) is considered identical to the corresponding code point in the
range U+0061..U+007A (corresponding to characters LATIN SMALL LETTER A
to LATIN SMALL LETTER Z). The rule above has the effect of making DOI
names case-insensitive only when testing for equivalence and only with
respect to the Basic Latin Unicode block. It does not restrict DOI names
to containing only uppercase or lowercase letters. EXAMPLE 1: The
following DOI names are equivalent because U+0053 LATIN CAPI-TAL LETTER
S and U +0073 LATIN SMALL LETTER S are considered identical: •
10.5594/SMPTE.ST2067-21.2020 • 10.5594/sMPTE.sT2067-21.2020

DOI HANDBOOK 38 EXAMPLE 2: The following DOI names are not equivalent
because U+00C1 LATIN CAPITAL LETTER A WITH ACUTE and U+00E1 LATIN SMALL
LETTER A WITH ACUTE are not considered identical: •
10.26321/Á.GUTIÉRREZ.ZARZA.02.2018.03 •
10.26321/á.gutiérrez.zarza.02.2018.03 The advantages of case sensitivity
(librarian and publisher practice, human readability and expectations)
are outweighed by considerations of data integrity. Case sensitivity
practice across Internet applications varies: DNS is not, the rest of
URLs are except sometimes they aren't (this depends on the server), Unix
vs PC/Mac file names (Microsoft Windows in general is not
case-sensitive, Unix operating systems are always case sensitive),
markup language tags, etc. can all cause unexpected problems and one
cannot guarantee that any particular piece of software will respect case
sensitivity and not conflate two DOI names intended to be different.
Some search engines and directories are partially case sensitive.
Different web browsers may differ in case sensitive handling (web
browser developers have advised that "authors should not rely on
case-sensitivity as a way of creating distinct identifiers, unless they
are designing solely for a truly standards-compliant browser"). This
argued in favor of limited case insensitivity being the safer, and more
robust, option for future evolution and development of the DOI System.

4.3.5 CONSIDERATIONS ABOUT THE USE OF CHECK DIGITS IN DOI NAMES The DOI
System does not itself make use of check digits. This is deliberate, for
a number of reasons: • ability to include an existing identifier string
as a prefix in a DOI without any alteration: some common strings like
ISO identifiers already have a check digit in them which act as aids to
readability or keyboard data entry in the absence of any automated
protocol correction; • performance considerations if a check sum is
calculated at each resolution; • · identifier schemes such as URL have
no check digit: the underlying TCP/IP protocol they use has an
error-correction component. This aids creation and use. However, other
applications may make use of check digits, so a checksum digit may be
inserted into a DOI name if it would be useful for some other
application. Use of checksums in a particular DOI System application can
be introduced as a rule of that application by the Registration Agency
concerned. An example is the EIDR application, where the check character
is computed only over the DOI suffix. It does not include the prefix
because if the prefix is wrong, it is highly probable that the DOI name
will go to an incorrect resolution system anyway. The EIDR registry
separately validates the prefix of any DOI name sent through its API.

4.4 REPRESENTATION FORMATS

4.4.1 VISUAL MEDIA When presented visually, a DOI name should be
preceded by a lowercase "doi:" unless the context clearly indicates that
a DOI name is implied. The "doi:" label is not part of the DOI name
value. EXAMPLE: the DOI name "10.1006/jmbi.1998.2354" is displayed and
printed as "doi:10.1006/jmbi.1998.2354". In print, to let the readers
know that the DOI name is actionable, Registration Agencies may elect to
use the HTTP Proxy form (see 3.5.4). It is then advantageous to use some
convention of showing both the plain DOI name and a way to resolve it
online (a shorthand way of saying "the DOI name for this article is
10.1002/prot.999 and current information may be found on the web through
https://doi.org/10.1002/prot.999" or "...available via
https://doi.org/..."). When prepended with "doi:", this presentation
format is equivalent to the URI syntax if the DOI prefix and suffix
consist solely of unreserved characters as defined in IETF RFC 3986. DOI
HANDBOOK 39 NOTE: This presentation can be ambiguous since multiple code
points or sequenc-es of code points can result in similar presentations.
For example, U+002D HYPHEN-MINUS, U+2212 MINUS SIGN and U+2013 EN DASH
are rendered as similar glyphs. As another example, the abstract
character "á" can be represented by either the code point U+00E1 or the
sequence of code points \<U+0061, U+0301\>. As detailed at 3.6, the URI,
URN and HTTP Proxy forms resolve these ambiguities.

4.4.2 URI FORM Where a DOI name is expressed as a URI (as specified in
IETF RFC 3986), it conforms to the "doi" scheme specified in the DOI URI
Scheme specification. EXAMPLE: The DOI name
"10.26321/á.gutiérrez.zarza.02.2018.03" can be presented in the URI form
"doi:10.1006/%C3%A1.guti%C3%A9rrez.zarza.02.2018.03".

4.4.3 URN FORM Where a DOI name is expressed as a URN (as specified in
IETF RFC 8141), it uses the "doi" namespace, as specified in the
Namespace Registration for Digital Object Identifier (DOI). EXAMPLE The
DOI name "10.26321/á.gutiérrez.zarza.02.2018.03" can be present-ed in
the URN form "urn:doi:10.1006/%C3%A1.guti%C3%A9rrez.zarza.02.2018.03".

4.4.4 HTTP PROXY FORM Where a DOI name is expressed as a URL (as
specified in IETF RFC 3986), the URL shall be created by
percent-encoding the result of concatenating the string
"https://doi.org/" with the percent-encoded DOI name (see 3.8). EXAMPLE
The DOI name "10.26321/á.gutiérrez.zarza.02.2018.03" can be present-ed
in the HTTP PROXY form
"https://doi.org/10.1006/%C3%A1.guti%C3%A9rrez.zarza.02.2018.03 As
detailed in 1.5.1, issuing an HTTP GET request at that URL resolves the
DOI name. Other HTTP proxy forms starting with the
string"https://dx.doi.org" are dep-recated.

4.4.5 OTHER Specific representations may be agreed to meet special
technical requirements. For example, the joint ANSI / Society of Cable
and Telecommunications Engineers standard "Digital Program Insertion
Cueing Message for Cable" (SCTE 35:2013) de-fines (among other things)
the standard method for cable TV systems to include EIDR DOI names
in-band with the programs being broadcast. It uses a compact lossless
EIDR representation rather than the full ASCII DOI string. This also
makes use of the resolvability of DOI names, suggesting that IDs so
carried can be resolved via an out-of-band mechanism to collect more
data. DOI names may also be presented in a shortened version via the
shortDOI service: see 5.5.

4.5 AVOIDING AND RESOLVING AMBIGUITIES WHEN PRESENTING OR EXCHANGING DOI
NAMES As discussed at 3.3, the flexibility that comes with Unicode can
introduce ambiguities when representing or exchanging DOI names. The
following discusses approaches to mitigate these ambiguities.

DOI HANDBOOK 40 The DOI name can be represented using a form that is
unambiguous. In particular, the URI, URN and HTTP Proxy forms specified
at 3.5 are self-identifying and appropriate for both human consumption
and machine exchange. In these forms, code points that fall outside a
very small set of unambiguous code points are transformed, using a
process called percent-encoding, into a sequence of unambiguous code
points. Strictly for machine exchange, the DOI name can be serialized as
a UTF-8, UTF-16 or UTF-32 string. A Registration Authority can choose
code points exclusively from the Unicode Basic Latin block when crafting
DOI suffixes.

4.6 UTF-8 SERIALIZATION UTF-8 is a common Unicode serialization scheme
that encodes each Unicode code point as an unsigned byte sequence of one
to four bytes in length. UTF-8 has the useful property that Unicode code
points in the Basic Latin block are mapped to their US-ASCII equivalent.
EXAMPLE 1: The Japanese word \### (nihongo) corresponds to the sequence
of code points \<U+65E5, U +672C, U+8A9E\>. This is serialized to the
UTF-8 string \<E6 97 A5 E6 9C AC E8 AA 9E\>. EXAMPLE 2: The English word
"bye" corresponds to the sequence of code points \<U+0062, U+0079,
U+0065\>. This is serialized to the UTF-8 string \<62 79 65\>. For
further information on UTF-8 see the Unicode Standard, 3.10.

4.7 PERCENT-ENCODING The percent-encoding algorithm specified at RFC
3986 is applied whenever a DOI name is used in the path component of a
URL, such as in the HTTP Proxy Form (3.5.4) or when calling an HTTP API
(10.3). This algorithm achieves two objectives: preventing conflict with
characters with special meaning in URLs, e.g., "/", and mapping
non-US-ASCII characters to a sequence of US-ASCII characters. The
percent-encoded representation of a DOI name is formed by first
apply-ing the following algorithm to each of its prefix and suffix
separately: 1. the ordered sequence of Unicode code points of the DOI
Prefix or Suffix is expressed as a UTF-8 String (see 3.7), without the
byte order mark and without any normalization; 2. for every byte in the
UTF-8 String: a. output the byte unmodified if the byte is one of the
following: ALPHA , DIGIT , "-" , "." , "\_" , "\~", "!" , "\$" , "&" ,
"'" , "(" , ")" , "\*" , "+" , ";" , "=" , ":", or "@" b. otherwise,
replace the byte with the US-ASCII byte triplet resulting from
percent-encoding the byte. Second, the resulting encoded prefix and
suffix are concatenated, separated by a "/". The ALPHA and DIGIT
character sets are specified at IETF RFC 3986. The "," byte is
percent-encoded to allow percent-encoded DOI names to be used in Which
RA? Service requests (see 5.6). EXAMPLE: The DOI name 10.1000/456#789 is
percent-encoded to "10.1000/456%23789". Thus the web browser does not
encounter the bare "\#", which it would normally treat as the end of the
URL and the start of a fragment, and so sends the entire string off to
the DOI network of servers for resolution, instead of stopping at the
"\#".

DOI HANDBOOK 41 4.8 INTEGRATION OF OTHER IDENTIFIER SCHEMES A DOI name
shall not be used as a replacement for other identifier schemes such as
ISAN, ISBN, ISRC, ISSN, ISTC, ISNI and other commonly recognized
identifiers, but when used with them it can enhance the identification
functionality provided by those systems with additional DOI System
functionality, and thus, provide interoperability with existing
identifier schemes. This section explains the different ways other
identifier schemes can be integrated. For more considerations about
identifier interoperability, see Identifier Interoperability factsheet
on the DOI web site.

4.8.1 SPECIFICATION OF ANOTHER IDENTIFIER IN SYSTEM METADATA The
existence of other existing identifier(s) for a referent is incorporated
into the System Metadata Declaration. With this requirement, an existing
legacy scheme can be used by any automated processes which pick up
structured metadata from a DOI System service, using the System Metadata
declaration of this referent.

4.8.2 INCORPORATION OF AN EXISTING IDENTIFIER INTO A DOI NAME An
existing identifier scheme can be included in the DOI syntax. PURPOSES
DOI names can incorporate established identifiers (like ISBN, ISAN,
ISWC, PII, or any proprietary identifier) to allow integration with
existing systems. Use of DOI name allows ready interoperability with
existing abstraction identifiers, with associated manifestation
identifiers and other metadata; with rights metadata; and builds on what
is practical in each sector. CONSIDERATIONS TO BE TAKEN INTO ACCOUNT
Where syntax rules permit the incorporation of an existing identifier
from another scheme as part of the DOI name, such rules do not form part
of ISO 26324 but are documented separately by the registration
authority. In such cases, attention is drawn to the following points. •
The same referent shall be denoted by both the DOI name and the included
identifier string, to the degree that is necessary to distinguish it as
a separate entity within each identifier scheme. • Within the DOI System
itself, the DOI name is an opaque string. No definitive information
relating to the other identifier scheme should be inferred from the
specific character string used for a DOI name, and the DOI name is not
guaran-teed to be usable in any non-DOI applications designed for the
other identifier scheme. • Specific syntax rules for the incorporation
of an existing identifier from another scheme shall be maintained by the
ISO 26324 Registration Authority. EXAMPLES Examples 1 and 2 show the
incorporation of an ISBN and an ISSN into a DOI name. Other agreed
syntaxes for integration are also possible. Example 3 shows that the DOI
name is not a replacement for the other identifier scheme. • Example 1
10.978.86123/45678 shows a possible incorporation of an ISBN
(978-86-123-4567-8) into a DOI prefix and suffix. • Example 2
10.1038/issn.1476-4687 shows a DOI suffix using an ISSN. • Example 3
10.97812345/99990 is a DOI name. It cannot be validly submitted to an
ISBN point-of-sale ordering system, or converted to a GS1 bar code for
use as an ISBN bar code. It does not conform to the

DOI HANDBOOK 42  ISBN syntax. 978-12345-99990 is an ISBN. It cannot be
validly submitted to a DOI resolution service; it does not conform to
the DOI syntax. However both identifier strings have the same referent.

4.8.3 LINKAGE OF DOI NAMES TO ANOTHER REGISTRY A business relationship
can be built to facilitate the inclusion of another identifier scheme in
the DOI syntax, by collaboration between the DOI Foundation and the
relevant registry. Where such collaboration is agreed, new potential may
be un-locked: the ISBN-A application is an example of the linkage of DOI
names to an existing registry. For more information, see DOI System and
the ISBN System.

4.8.4 COMPLEMENTATION OF OTHER IDENTIFIER SERVICES The DOI System
functionality can be offered to complement other identifier services
which are available through other parties, for example, for the
resolution of identifiers in a variety of contexts. Services using an
identifier can be offered by multiple providers. Rules of certain
identifier systems can necessitate the use of only specified preferred
service providers; in such cases, the application of the identifier
shall follow the rules of the relevant registration authority. Each
registration authority for an identifier scheme retains autonomy in
determining rules for usage within its own scheme or community. The DOI
Foundation maintains current information on agreed specific mechanisms
for use with other identifier schemes.

DOI HANDBOOK 43 Chapter 4

SYSTEM METADATA

This chapter explains the basis for one of the main technical components
of the DOI System, the DOI data model, and its ability to ensure
interoperability of DOI name metadata assigned through metadata schemes.

In This Chapter 5.1 Introduction to System Metadata
................................................ 45 5.2 Metadata
Requirements According to ISO 26324 .......................... 46 5.3
System Metadata Model
........................................................... 47 5.4
Metadata Interoperability
........................................................... 49 5.5
Automated Integration of Metadata
............................................. 50

DOI HANDBOOK 44 5.1 INTRODUCTION TO SYSTEM METADATA Without metadata, an
identifier is of very little value. Metadata, which may be defined in
this context as information about an identified referent, provides human
beings or machines with the data they need to enable them to make use of
that identified referent. Metadata may include names, identifiers,
descriptions, types, classifications, locations, times, measurements,
relationships and any other kind of information related to a referent.
Metadata may be grouped in different ways and it is useful to define
terminology for the different metadata groups that will exist for an
identified entity (referent). The following definitions are used when
discussing DOIs: • DOI System Metadata: Metadata for a referent that is
defined in the ISO 26324 standard and also provided in Section 10.1 of
this document. Its purpose is to ensure consistent description of the
referent within a referent sub-type and to enable users to distinguish
one DOI record from another. This metadata is collected and stored by
registration agencies. • Registration Agency Metadata: Any metadata
stored by a registration agency as part of its activities. This includes
DOI System Metadata, but will often extend to other metadata that
facilitates applications beyond the distinguishing of records of the
same referent subtype. • Referent metadata: All metadata that exists
about the referent regardless of where it is stored by a registration
agency or not. • Basic Metadata: Part of DOI System Metadata that allows
sufficient additional metadata to define what the referent is. Fields
necessary will depend on the Referent Type and Sub-Type. •
Administrative Metadata: Descriptive elements used in DOI System
Metadata about the DOI Record.

Registration agencies are responsible for the collection and storage of
metadata. The registration agency determines where the metadata is
stored and provides access. In some cases this may be via the Handle
System. But there is no requirement for metadata records to be in the
DOI record in the Handle System. There are two ways in which every
Registration Agency (RA) is bound to deal with metadata as illustrated
below: • An RA will gather input metadata from referent providers
(typically, descriptions of the referents and associated rights and
policies). • An RA will need to provide some level of output or service
metadata to support DOI system services.

Figure 9 Input and service metadata Input metadata will provide some,
but not necessarily all, of the service metadata.

DOI HANDBOOK 45 In some cases, a metadata declaration will itself be a
complete DOI System service.

5.2 METADATA REQUIREMENTS ACCORDING TO ISO 26324 This section describes
the requirements on System Metadata specified in ISO 26324.

5.2.1 GENERAL REQUIREMENTS ON METADATA According to ISO 26324, the
referent shall be described unambiguously and pre-cisely by System
Metadata, based on a structured data model that enables the referent of
a DOI name to be associated with metadata of any desired degree of
precision and granularity to support identification, description and
services asso-ciated with a referent. This is designed to do the
following: • promote interoperability within networks of DOI users by
enabling independent systems to exchange information and initiate
actions from each other in trans-actions involving DOI names Since DOI
names can be assigned to any type of object, such interoperability can
be across different types of content (for example, audiovisual, music
and text). • ensure minimum standards of quality of administration of
DOI names, and facilitate the administration of the DOI system as a
whole.

5.2.2 REQUIREMENTS ON METADATA FUNCTIONS According to ISO 26324, System
Metadata should support the following functions: • generic mechanism for
handling complex metadata for all different types of in-tellectual
property For example, instead of treating sound carriers, books, videos,
and photographs as fundamentally different things with different (if
similar) characteristics, they are all recognized as creative works with
different values of the same higher-level attributes, whose metadata can
be supported in a common environment. • interoperability of metadata
across applications, with reference to: • media (for example, books,
serials, audio, audiovisual, software, abstract works, visual material)
• functions (for example, cataloguing, discovery, workflow, and rights
man-agement) • levels of metadata (from simple to complex) • semantic
barriers • linguistic barriers • functional granularity, making it
possible to identify an object whenever it needs to be distinguished

5.2.3 REQUIREMENTS ON METADATA REGISTRATION According to ISO 26324,
metadata describing and identifying the referent to which the DOI name
is being assigned shall be recorded promptly and accurately. In
addition: • Referent subtypes and basic metadata model definitions shall
be placed in a repository to facilitate interoperability across selected
existing schemes. Basic metadata (if needed) is specified by each
registration agency for its referent subtypes. • The metadata shall meet
the minimum requirements of System Metadata includ-ing Basic Metadata
for the relevant sub-type of referent The DOI Foundation helps
registration agencies to coordinate basic metadata definitions where
more than one registration agency works on the same referent sub-type

DOI HANDBOOK 46 5.3 SYSTEM METADATA MODEL The System metadata model can
be extended to meet the needs of the Registration Agencies.

5.3.1 SYSTEM METADATA MODEL POLICY DOI System metadata model policy is
concerned with the internal management and exchange of metadata between
Registration Agencies (RA) within the RA network, and is designed to: •
promote interoperability within the network of DOI system users • ensure
minimum standards of quality of administration of DOI names by RAs and
facilitate the administration of the DOI System as a whole POLICY ON
SYSTEM METADATA DECLARATION A metadata declaration must be made for
every entity identified with a DOI name according to the following
principles: • The declaration must contain a minimum set of mandatory
metadata which is defined through the DOI System Metadata. This
specification is designed to be as limited in scope as possible, and it
is applicable to any entity identifiable by the DOI System. • Additional
metadata can be declared. They should be based on an agreed metadata
exchange schema if metadata interoperability is required with other
Registration Agencies (RA). DOI data model policy places no restrictions
on the form and content of input and service metadata declarations of a
Registration Agency (RA), except insofar as input metadata must support
the minimum requirements implicit in the DOI System Metadata. RAs may
specify their own metadata schemes and messages, or use any existing
schemes in whole or part for their input and service metadata
decla-rations. POLICY ON DOI NAME ADMINISTRATION The second aim of DOI
data model policy is to ensure minimum standards of quality of
administration of DOI names by Registration Agencies (RA),and facilitate
the administration of the DOI System as a whole. This aim may also be
seen as support-ing the first aim of interoperability, but it
specifically addresses the need to ensure that a prospective RA is
competent to issue DOI names responsibly and that ambiguous DOI names do
not enter the network. The policy provides a simple test of an RA's
competence: the ability to make a DOI System Metadata Declaration, which
requires that the RA has an internal system which can support the
unambiguous allocation of a DOI name, and is fundamentally sound enough
to support interoperability within the network. In addition, the policy
requires that RAs maintain a record of the date of allocation of a DOI
name, and the identity of the registrant on whose behalf the DOI name
was allo-cated. The existence of a System Metadata expression for each
DOI name helps with the goal of persistence since this ensures that the
referent for each DOI name is described sufficient for the referent to
be known. So, the referent to which a DOI is assigned to is known
through the expression of the System Metadata for that referent. The DOI
System Metadata model policy also exists to support the future
development of mechanisms for facilitating the administration of the DOI
System as a whole. This might be done, for example, through the use of
terms registered as types/sub-types, to classify DOI names, or services.

DOI HANDBOOK 47 5.3.2 DOI SYSTEM METADATA The assignment of a DOI name
requires that the registrant provide metadata describing the object to
which the DOI name is being assigned. This metadata shall consist of a
common elements plus basic metadata for the referent subtype (as defined
in the System Metadata). BASIC INFORMATION CONTAINED IN THE DOI SYSTEM
METADATA The DOI Metadata elements should answer basic questions such
as: • What is the DOI name assigned to the referent? • Is the referent
commonly referenced with another identifier? • What is the referent
usually called? • What is the primary and secondary type of the referent
(examples of primary types are: creative work, party, event)? It answers
other questions about the referent depending on the primary type of the
referent, and the following administrative questions: • Which
Registration Agency issued this DOI name? • When was the declaration
issued? • Which version is it? NOTE Registration Agencies can add new
values to open lists of allowed values for the System Metadata: see
4.3.4. PURPOSE OF THE SYSTEM METADATA The purpose of the System Metadata
is to allow: • recognition Recognition in this context means that the
System Metadata should be suffi-cient to show clearly what kind of thing
is the DOI referent (by various classifica-tions), and allow a user to
identify with reasonable accuracy the particular thing (by various
names, identifiers and relationships). These two are complementary, for
it is possible to know that something is (for example) a movie or a DVD
without knowing that it is "Casablanca", and vice versa. Recognition is
required for the discovery of referents, and also to provide information
to a user when a ref-erent is discovered, whether by intent or accident.
The user of metadata may be a person or a machine. The structure of the
System Metadata is sufficient to provide a unique description of a
referent (disambiguation), since further specialized metadata elements
may be required which is specified as Basic Metadata per Referent
SubType. A unique description can in fact always be achieved by adding
additional descriptive text to a referent, but this is not a
satisfactory way if the additional text is being used in place of a
formal classification, measurement, identifier, time or other structured
contextual metadata, as it undermines the second goal of
interoperability • interoperability Interoperability in this context
means that System Metadata from different DOI Registration Agencies may
be combined or queried by the same software ap-plication without
requiring semantic mapping or transformation. Interoperability is
achieved when data elements or their values are common to diverse
metadata schemas. The System Metadata provides this directly by
mandating a common set of core elements and classifications, but this of
course supports only limited interoperability.

5.3.3 ADDITIONAL METADATA Additional metadata can be declared. They
should be based on an agreed metadata exchange schema if metadata
interoperability is required with other Registration Agencies (RA). XML,
RDF or JSON schemas may be used.

DOI HANDBOOK 48 The DOI System Metadata Model specifies the data
elements and allowed values of the metadata exchange schemas (see 10.1).

5.3.4 DATA MODEL EXTENSION AND MAINTENANCE Registration Agencies can
request: • the addition of new terms to the DOI System Metadata model,
or the publica-tion of additional metadata schemas • the addition of new
values to open lists of values of the DOI SubTypes and/or Basic Metadata
specification Authority to make changes in the existing DOI
specifications lies with the Metada-ta Working Group. A fundamental role
of the DOI Foundation is to provide assurance to users that the changes
have been peer- reviewed, tested in practical implementations, and are
based on sound principles. For more information, see 7.4.

5.4 METADATA INTEROPERABILITY The aim of DOI System Metadata model
policy is to promote interoperability within the network of DOI name
users. It does this by providing ways of achieving seman-tic
compatibility between different Registration Agencies.

5.4.1 MOTIVATIONS FOR INTEROPERABILITY Standardization of any kind is
driven by a need for interoperability. If a Registration Agency (RA) is
issuing DOI names for referents for use within a private domain where
that RA is able to command all aspects of metadata gathering and output,
then it has no need for standardization or conformance with DOI data
model obligations. The RA will lay out its schemas and declarations, and
its providers and users should conform to them. Such a situation is
described as restricted use of the DOI System, and applies typically
where an organization becomes an RA for the specific purpose of issuing
DOI names for use only within its own private organiza-tion. However,
such isolation is unusual. Normally, when a DOI name is issued to a
referent, one fundamental assumption may be made about interoperability:
the RA or the referent provider may wish (now or in the future) that the
DOI name should be available for use in services provided by other RAs.
For example, where several RAs are issuing DOI names to journal articles
from different publishers, it is likely that some RAs and publishers
will want their DOI names to be included in journal-related services
supported by other RAs. In a similar way, many RAs will want DOI names
issued by other RAs to be available for inclusion in services they
themselves are providing. Such interoperability is one of the principal
benefits of the DOI System. As the RA network grows, such requirements
are emerging, and where specific opportunities do not yet exist they are
anticipated. In such circumstances neither the RA nor the referent
provider wishes to issue a second DOI name for the refer-ent, nor to
provide and capture the input metadata all over again from its source.

5.4.2 ACHIEVEMENT OF INTEROPERABILITY Any DOI name which is intended for
interoperability --- that is, which has the possibility of use in
services outside of the direct control of the issuing RA --- is subject
to the metadata policy: • The System Metadata ensures that the minimum
set of metadata held by differ-ent RAs is consistent. The figure below
shows what applications can assume about a referent across reg-istration
agencies. In this example, of the application can process System
Metada-ta about a DOI name managed by RA1 and another DOI HANDBOOK 49
managed by RA2. To be able to process this metadata, the application
uses the System Metadata Model agreed between registration agencies. The
System Metadata is intended to allow development of cross RA
applications. If an application is RA-aware it can use other metadata
beyond the System Metadata.

Figure 10 Achievement of interoperability

5.5 AUTOMATED INTEGRATION OF METADATA The DOI Foundation recognizes that
the automated integration of metadata is the key to realizing the full
potential of the DOI System. This is also the underlying objective of
the Semantic Web and Linked Data: that the Web should be seen as a
medium for structured, interlinked and machine-processable information,
as much as, in its current form, a network of documents presenting the
information for human consumption. The DOI System Metadata exists to
provide a basis of good practice and a start point for the integration
of metadata for different DOI referents. Initiatives such as Linked Open
Data provide further essential infrastructure, but only in technology
and syntax: they do not provide solutions at the level of shared meaning
(semantic alignment) for the automated integration of different datasets
which can allow services from different RAs and other parties to
interact fully without human inter-vention or a plethora of one-to-one
"silo" solutions. The key to this is the development of well-structured
metadata schemas and of services which make use of the semantic mapping
capabilities of the DOI System Metadata Model. The DOI Foundation will
provide support to their RAs where they choose to co-operate in the
development of such services.

DOI HANDBOOK 50 Chapter 5

DOI IDENTIFIER / RESOLUTION SERVICES

This chapter describes the identifier / resolution services included in
the DOI System package.

In This Chapter 6.1 Identifier / Resolution Services based on the Handle
System .......... 52 6.2 DOI Directory
..........................................................................
55 6.3 DOI Resolvers
........................................................................
57 6.4 DOI Resolution Functions
......................................................... 58 6.5
ShortDOI Service
..................................................................... 62
6.6 Which RA? Service
.................................................................. 63

DOI HANDBOOK 51 6.1 IDENTIFIER / RESOLUTION SERVICES BASED ON THE HANDLE
SYSTEM The DOI System offers DOI identifier / resolution services
through the Handle System which meets the functional requirements
defined by ISO 26324.

6.1.1 ISO 26234 FUNCTIONAL REQUIREMENTS ON THE RESOLUTION SYSTEM
According to ISO 26234, the technology deployed to manage the resolution
of the DOI name shall support the functions listed below: • internet
compatible: transmission via the global information system that is
logically linked by a globally unique address space and communications •
first class naming: identifiers resolved by the system shall have an
identity independent of any other object • unique identification: the
specification by an identifier string of one and only one referent •
functional granularity: it shall be possible to separately resolve a
referent when-ever it needs to be distinguished • data typing: The
extensible definition of constraints placed upon the interpretation of
certain data entries in a resolution record, such that data values with
similar constraints can be grouped and treated in the same way. •
resolution services: the resolution record contains information
indicating how to access services relating to the DOI name Resolution
requests should be capable of returning resolution records with all
associated values of current information, individual values or all
values of one data type. • designated authority: The administrator of an
identifier shall be securely identified and capable of transfer. •
appropriate access to resolution records: Changes to a resolution record
shall be recorded and shall be capable of providing access to the data
on which the administrator depends and privacy and confidentiality from
those who are not dependent on it. • DNS independent but compatible: not
reliant on the Domain Name System (DNS), but capable of working with DNS
domain naming and resolution services • granularity of administration:
DOI names can be administered individually or in groups. • scalability:
• efficient and infinitely scalable protocol • no limitations on
absolute number of identifiers assigned or length of identifier string •
unicode compliant

NOTE The regular update of the DOI records is crucial to maintain
quality services.

6.1.2 INTRODUCTION TO THE HANDLE RECORD With the Handle System, a Handle
is resolved to a set of elements called the Handle Record (the DOI
record in case of a DOI name). An element is a typed data. Predefined
types exist in the Handle System and new types can be added at any time.
For example, a DOI name could resolve to a Java servlet, or other
dynamic mechanism. An element inside a DOI record may be: • a link to a
resource: web address, IP address, etc. • metadata: description, type,
terms and conditions, ownership, etc. of the entity represented by the
DOI name • security information: public key, digital signature, etc. DOI
HANDBOOK 52 • administration information: administrator of the DOI
record with permissions • state information: entity status, etc. The
following figure shows a DOI record example.

Figure 11 DOI record example An element consists of: • an index: unique
element identifier inside the DOI record • a global and registered type
(for example, URL, description, IP address, email address, etc.) • a
value (data) • a permission level: specifies if the value is publicly
available or not and if it can be changed by an authorized administrator
• a timestamp • a Time To Live (TTL): specifies how long the element
value can be cached before the information source should again be
consulted NOTE An element inside a Handle Record can point to one or
several Handles or to one or several elements in the same or in another
Handle Record.

6.1.3 HANDLE SYSTEM SERVICE ARCHITECTURE This section introduces briefly
the Handle System services. For more information, see Digital Object
Identifier Resolution Protocol (DO-IRP) Specification. The Handle System
consists of a single distributed Global Handle Registry (GHR), and
unlimited number of Local Handle Services (LHS): • Identifiers (called
Handles) are managed by LHSs. Handles under the same prefix are managed
by the same LHS. • The GHR stores the information necessary to locate
the LHS responsible for any Handle in the system.

To resolve a Handle, a Handle System client will first connect to the
GHR which will redirect it to the LHS responsible for the requested
Handle. To understand in more details how the GHR and LHS work, it is
necessary to intro-duce first the prefix Handle concept. INTRODUCTION TO
PREFIX HANDLES (0.NA PREFIX) Specific Handles are used in the Handle
System to represent the prefixes: • The Handle of a prefix is in the
format "0.NA/`<prefix>`{=html}

DOI HANDBOOK 53 • The record of a prefix Handle (record returned by
Handle resolution) contains administration data for managing the prefix.
For example, 0.NA/10.100 record stores the location (service
information) of the LHS responsible for the resolution of DOI names
under 10.100 (see also a prefix handle example in section 10.5). GLOBAL
HANDLE REGISTRY (GHR) The GHR is a distributed registry whose operation
is managed collaboratively by the DONA Foundation and multiple
organizations. An organization that is authorized by the DONA Foundation
to participate in the distributed administration of the GHR is referred
to as a Multi-Primary Administrator (MPA). Each MPA is "credentialed"
and allotted a zero-delimiter prefix by the DONA Foundation. It operates
its own GHR Service in accordance with the Foundation procedures, and
coordinates it with the other MPAs and DONA on a multi- primary basis.
The DOI Foundation is an MPA and was allotted the prefix 10. The GHR
consists of: • the GHR services of the MPAs called MPA GHR Services •
the GHR Service operated by the DONA Foundation An MPA GHR Service
provides: • first-level resolution of Handles The GHR is the first
access point for any client requesting a Handle resolution. Based on the
prefix Handles hosted in the GHR, it redirects the client to the Lo-cal
Handle Service (LHS) responsible for this Handle. • administration for
its assigned credential prefix The MPA GHR Service allows the creation
and maintenance by an authorized administrator of the one-delimiter
prefix Handles derived from the credential prefix. All prefix Handles
managed in a GHR Service are automatically copied across all the other
GHR Services. The GHR stores only the records of zero- and one-delimiter
prefix Handles (up to the limit of one million). The other prefixes are
managed through LHSs.

Figure 12 Global Handle Registry (GHR) LOCAL HANDLE SERVICE (LHS) An LHS
is operated independently by a service provider and is assigned one or
several prefixes. LHS INSTANCES: HANDLE AND PREFIX There are two types
of LHS instances:

DOI HANDBOOK 54 • Handle LHS A Handle LHS hosts and provides resolution
and administration of all Handles un-der a given prefix. • Prefix LHS A
Prefix LHS hosts and provides resolution and administration of prefixes
derived from a given prefix. NOTE Administration means creation,
modification and deletion of the Handle Records. It requires
administrator permissions. For more information, see Digital Object
Identifier Resolution Protocol (DO-IRP) Specification. The same LHS can
provide both instances and can be responsible for any number of
prefixes.

Figure 13 The two types of Local Handle Service (LHS) Both these LHSs
operate with the same LHS software and are configured the same way.
SERVICE SITES OF AN LHS Handle System service components are scalable
and extensible to accommodate any large amount of service load. An LHS
may consist of multiple service sites, each hosting a full replica of
the Handles managed by the service. A site may be a primary site (it
means that it can be used for administrative operations: to create,
modify or delete Handle Records stored in its database) or a mirror site
(no administrative operation is possible). Each service site may also
consist of a cluster of computers working together, each with a
particular subset of the Handles managed by the service. Having multiple
service sites avoids any single point of failure and allows load
balancing among these service sites. Using multiple servers at any
service site distributes the service load into multiple server processes
and allows less powerful computers to be utilized for the name service.

Figure 14 Service sites of an LHS

6.2 DOI DIRECTORY The DOI Directory is a virtual service consisting of
Handle System services (see 5.1.3) and web proxies located and
configured to provide highly reliable resolution, administration, and
backup for all DOI names, regardless of the varying administrative
arrangements of the Registration Agencies (RA). This approach provides
the flexibility RAs need to develop individual business models and meet
customer requirements while guaranteeing reliable overall service. DOI
HANDBOOK 55 The DOI names are stored in Local Handle Services (LHS)
which are usually managed by the DOI technical support service provider
but may also be operated by the RA. NOTE All DOI names must be
registered in the DOI Directory.

6.2.1 LOCAL HANDLE SERVICES (LHS) USED IN THE DOI SYSTEM The DOI
Foundation has contractual agreements for provision and persistence of
the Handle System with the DOI technical support service provider who: •
provides technical and operational support for the DOI System • usually
manages the Local Handle Services used in the DOI System (DOI LHS). A
Registration Agency (RA) can choose to install and use the Handle LHS
responsi-ble for their DOI names (A Prefix LHS will always be managed by
the technical support service provider.).

6.2.2 DOI LHS OPERATED BY A REGISTRATION AGENCY A Registration Agency
(RA) can run the Local Handle Service(s) responsible for the DOI names
of their registrants. This may the best choice for an RA who: • wish to
have immediate control of business-critical infrastructure components
such as DOI registration • plan to implement high performance standards
for administration and resolution by choosing levels of performance
appropriate to their application In this case, the DOI technical support
service provider will run a mirror service of this LHS so that they have
a copy of the DOI name database managed by the RA. The DOI Foundation
requires that RAs be responsible for modification of the configuration
of their Handle servers to allow a secondary server installation at the
DOI technical support service provider. In the illustration below, if
the RA who was allocated the prefix 10.550 wants to run their own LHS,
then the technical support service provider would run one of the mirror
LHSs.

Figure 15 Handle LHS operated by a Registration Agency NOTE Choosing the
option of running their own LHS will require more technical expertise on
the part of the RA. If an RA is interested in running a DOI LHS it is
wise to schedule a technical overview meeting with the

DOI HANDBOOK 56 staff of the DOI technical support service provider. To
set this up or to answer any questions please send email to the DOI
technical sup-port service provider at doi-admin@doi.org.

6.3 DOI RESOLVERS To be able to use the core resolution service of the
DOI System, a DOI resolver is required. A DOI resolver is a client of
the Handle System.

6.3.1 DOI PROXY FOOTNOTE: An earlier proxy address (https://dx.doi.org)
is deprecated and its use is discouraged. With the HTTPS Proxy Server of
the DOI System (https://doi.org) , users can resolve DOI names from any
standard web browser by using the URL syntax. For example, the
resolution of the DOI name "10.10.123/456" would be done from the
address https://doi.org/10.123/456. NOTE To enable the use of DOI names
in workflows that have already standardized on URNs, the DOI proxy
servers understand the substitution of a colon in place of the initial
slash in a DOI name. DOI names may therefore be expressed as URNs in the
doi.org domain by writing, for example, the DOI name 10.123/456 in the
form https://doi.org/urn:doi:10.123:456. However, a DOI suffix is
allowed to contain other slashes, and where these occur they must be
hex-encoded rather than replaced with a colon: for example, the DOI name
10.123/456ABC/zyz would become
https://doi.org/urn:doi:10.123:456ABC%2Fzyz, with the final slash
character encoded as %2F. DOI PROXY SERVICE CHARACTERISTICS The DOI
Proxy is accessible over IPv6, and supports DNSSEC. The DOI Proxy
consists of multiple servers running at multiple locations, with the
load distributed evenly across all servers. NOTE The core DOI name
resolution service is used by the DOI Proxy but is not constrained by
the DOI Proxy. DOI PROXY RESOLUTION FUNCTION The DOI Proxy supports the
single and multiple DOI resolutions: see 5.4. The resolution process is
as follows: 1. The DOI Proxy receives an HTTPS or HTTP request from a
requester for resolving a DOI name. The request is in the format
https://doi.org/`<doi-name>`{=html}?`<parameters>`{=html}. For more
information, see 10.2. 2. The DOI Proxy requests the DOI name resolution
from the GHR (or retrieves it from its cache, if the record is in its
cache and no authoritative query is done) which redirects it to the
responsible DOI LHS. Before sending the resolution re-quest, the DOI
Proxy decodes the percent-encoded DOI name if necessary (see Error!
Reference source not found.). 3. The responsible DOI LHS returns the DOI
record to the DOI Proxy. 4. The actions performed by the DOI Proxy
depend on the query parameters. Typically: • If the DOI record contains
a 10320/LOC element then the DOI Proxy interprets the XML code it
contains and embeds the resulting URL in an HTTP(S) redirect, and sends
it back to the requester (see 5.4.2). • Otherwise, the DOI Proxy
redirects the requester to the first URL element it finds in the DOI
record (see 5.4.1). NOTE To speed resolution, the proxy servers cache
DOI record values, with the TTL (Time To Live) set to one hour. This
means that if a DOI record value is changed, it can take up to one hour
before the new value is returned. This setting is specific to the
current proxy sys-tem and different DOI software clients could be
configured to behave differently. The de-fault Handle Record TTL setting
is 24 hours, which is a common TTL

DOI HANDBOOK 57 for Internet applications. While the one hour setting
currently holds for the DOI proxy, it would be best to design var-ious
DOI workflows assuming the more conservative 24 hour period. DOI PROXY
MAINTENANCE COMMITMENT The DOI technical support service provider and
the DOI Foundation are committed to maintaining the DOI Proxy in
perpetuity, as it is an essential component to maintaining the integrity
of the millions of instances of DOI name-based web links. Maintaining
the utility of those links over time will require maintaining both the
core DOI System and the specific gateway service, doi.org, that those
links refer-ence and so use to gain access to the core DOI System. This,
of course, is not at all unique and is just another variation on the
Internet theme of layering services on top of one another. doi.org is
itself dependent on the Domain Name System (DNS), which is itself
dependent on IP addressing and routing, etc.

6.3.2 CUSTOM DOI RESOLVERS Additional DOI resolvers can be built and
additional methods can be used to ac-cess the core DOI name resolution
system without interfering in any way with the ongoing operation of the
DOI Proxy. For more information, see 7.5.

6.3.3 DOI REST API The DOI REST API allows programmatic access to DOI
name resolution services us-ing HTTP(S). A REST API request can be made
by performing a standard HTTP GET. The API returns JSON. The DOI REST
API provides specifications for using the Handle System but avoids the
need for users to address the Handle System directly and in depth. The
API en-sures the portability of any code written to address DOI System
services and applications. For technical details, see 10.3. NOTE In
addition to Java, API libraries are available for Python, Perl, and C.

6.4 DOI RESOLUTION FUNCTIONS This section describes the resolution
functions provided through the DOI System. They are supported by the DOI
Proxy and the DOI REST API.

6.4.1 SINGLE DOI RESOLUTION The single resolution function of the DOI
System consists in returning to the requester the location stored as an
URL element in the DOI record. With the DOI Proxy, the requester is
redirected to this URL through an HTTPS request (see 1.5.1). The process
is as follows: 1. A user sends a DOI name resolution request to a DOI
resolver. 2. The DOI resolver sends a resolution request of the DOI name
to the GHR. The GHR redirects the resolver to the responsible DOI LHS
which returns the DOI record to the resolver. 3. The DOI resolver
retrieves the first URL element it finds in the list of DOI record
elements and returns this URL to the requester.

DOI HANDBOOK 58 6.4.2 MULTIPLE DOI RESOLUTION With the multiple DOI
resolution, multiple resources in potentially any format can be managed
in the DOI record. The multiple resolution is typically used to manage
several URLs of the same referent (see 1.6.1) or to select a different
URL according to various criteria. To manage multiple resources in the
DOI record, an element of the predefined type 10320/LOC is used. This
element allows specifying complex rules formatted in RDF/XML which can
be interpreted by the DOI resolver to retrieve the resources to be
returned to the resolution requester. For example, a resource may be
selected according to the context of the request (in particular, to the
country of the re-quester). For more information, see 10.4. The
following figure shows a DOI record containing a 10320/LOC element used
to retrieve URL(s). The 10320/ LOC element could also be stored at
prefix level, thus applying to all DOI names under that prefix.

Figure 16 Multiple DOI resolution (multiple URLs) The multiple DOI
resolution process is as follows: 1. A requester (user or application
process) sends an HTTP request to the DOI re-solver. 2. The DOI resolver
sends a resolution request of the DOI name to the GHR. The GHR redirects
the resolver to the responsible DOI LHS which returns the DOI record to
the resolver. 3. 3. The DOI resolver recognizes the 10320/LOC element.
Depending on the HTTP request features, the DOI resolver may interpret
the code it contains and return the interpretation result (for example,
an URL) to the requester; or it may return the raw XML code, or a list
of possible resources (for example, a list of URLs). If there are DOI
resolvers (other than the DOI Proxy) that do not understand the
10320/LOC type, these resolvers would ignore it and simply apply a
single DOI resolution request.

6.4.3 PARAMETER PASSING With the parameter passing feature, information
about the context of the request (for example, the particular user
making the request) can be included in the DOI resolution request sent
to the DOI Proxy. Different context expressed in the request may result
in different resolution results. Changes in context are predictable, and
do not require the original creator of the hyperlink to handcraft
different URLs for different contexts. Two URLs are involved in the
parameter passing feature: • the referrer URL: URL sent by the requester
(referrer) to the DOI Proxy and con-taining the DOI name to be resolved
and the context information • the referent URL: URL registered in the
respective DOI record (by the referent) and which may also contain
parameters The DOI Proxy combines the referrer URL with the referent URL
to create the out-bound link. It supports two different methods:

DOI HANDBOOK 59 • urlappend: simple method (see below) • OpenURL:
deprecated method (see Appendix) PARAMETER PASSING WITH URLAPPEND With
urlappend, key-value pairs can be passed to the out-bound link by
placing them in the referrer URL as follows:
https://doi.org/`<doi-name>`{=html}?urlappend=%3F`<key1>`{=html}=`<value1>`{=html}%26`<key2>`{=html}=`<value2>`{=html}...
The question mark (%3F) or the ampersand (%26) must be used before each
key-value pair. For example, the referrer URL
https://doi.org/10.1256/003590?urlappend= %3Fparam1=12345%26param2=6789
is combined with the referent URL https://
www.publisher.org/resource9876 to create the out-bound link
https://www.publisher.org/resource9876? param1=12345%26param2=6789 If
the referent URL already contains parameters then they may conflict with
the urlappend values. In the above example, the urlappend should start
with an am-persand character rather than a question mark character.

6.4.4 CONTENT NEGOTIATION Content negotiation refers to mechanisms
defined as a part of HTTP(S) that make it possible to serve different
representations of a resource at the same URL, so that the content
rendering software can specify which version fits their capabilities the
best. In the context of the DOI System, content negotiation allows
making a re-quest that favors content types specific to a particular
Registration Agency (RA) but which will also degrade to respond with a
more standard content type for other RAs. A content negotiated request
to a DOI resolver is much like a standard HTTP(S) request, except
server-driven negotiation will take place based on the list of
acceptable content types a client provides. The request is done by using
an HTTPS header "Accept" where the GET includes several content types
that are acceptable to the requesting client process (those that it
knows how to parse), each content type with a specific preference level
(quality factor). For example, Crossref RA uses content negotiation to
redirect all requests which are not for the content type "text/html" to
the metadata service managing the requested DOI name. To do so, the
10320/LOC element (which corresponds to the content type
"application/rdf+xml") is used in the DOI record to specify the redi-
rection to the respective metadata service. If the DOI resolver does not
support this content type then it will redirect to the URL defined in
the URL element (con-tent type "text/html"). This is illustrated in the
DOI name example below.

DOI HANDBOOK 60 Figure 17 DOI record example with RDF XML content type
Shown below is an Accept header for the content negotiated request,
listing both "application/ vnd.citationstyles.csl+json" and
"application/rdf+xml", and the metadata returned by the metadata
service. The requesting client wishes to receive CSL-JSON if it is
available, but can also handle RDF XML if CSL-JSON is unavailable. A
preference level ("q" factor) is used in the request to specify the
preferred choice.

DOI HANDBOOK 61 Figure 18 Content negotiated request with response

6.4.5 HANDLING OF RESOLUTION ERRORS IN THE DOI SYSTEM Actions which
result in an attempted resolution not being successful result in error
messages. These can be provided by Registration Agencies, or by the DOI
System centrally. The error page provided by the DOI System directs the
user to DOI help address (doi-help@doi.org) which is managed by the DOI
technical support service provider: • If the problem is with the Handle
System, the DOI technical support service pro-vider responds to the
sender appropriately. • If the DOI name is not found, a special handling
is performed (see below). "DOI NOT FOUND" AND "DOI PREFIX NOT FOUND"
ERRORS The entered DOI name or DOI prefix may not be found, for example,
when resolution requests for DOI names are incorrectly formatted or the
DOI names do not exist. In that case, a response page is displayed with:
• details about the error To further assist users, the error response
system checks to see if a user has at- tempted to resolve a DOI prefix
only, or a DOI that contains multiple slashes or a trailing slash which
might be causing the error, and advises the user according-ly. • the
possibility for the user to send a report to the responsible RA If
required by an RA, the technical support service provider can configure
the DOI Proxy to automatically report the error message to the
responsible RA

6.5 SHORTDOI SERVICE The shortDOI service is a public service
(https://shortdoi.org/), open to anyone, that creates shortcuts to DOI
names which are often very long strings. The shortDOI service provides a
function similar to that which URL shortening services do for URLs. The
service creates short DOI names of the form 10/abcde and enables short
HTTPS URIs of the form https://doi.org/abcde that are ideal for use in
email, blogs, mobile messaging and more. (Note that shortDOIs are not
themselves DOI names and therefore do not conform to the ISO standard
syntax and other requirements. A shortDOI can only be created for an
existing DOI name.) The shortDOI service proxy server only resolves the
shortcuts, identically to the way the DOI Proxy only resolves full DOI
names. The service will either create a new shortcut, or return the
existing shortcut if one has already been created.

DOI HANDBOOK 62 For automated purposes, the shortDOI service can also be
used by simply append-ing the original DOI name to the URL for the
service. A format parameter can be used to specify how information is to
be returned. For further information, see the shortDOI service web page.

6.6 WHICH RA? SERVICE Which RA? is a simple service that has been built
to examine the type/value pairs returned from Handle resolution and
provide specific information that is available from the DOI Proxy. This
service returns the name of the DOI Registration Agency (RA) responsible
for a specific DOI name, or group of DOI names. The service is requested
by using the command https://doi.org/doiRA/`<doi-names>`{=html} where: •
`<doi-names>`{=html}: single percent-encoded DOI name or a list of
percent-encoded DOI names separated by commas Percent-encoded DOI names
are defined at 3.8. NOTE that shortDOI names are not supported. 0212 A
bit of JSON specifying the name of the RA is returned. For example,
resolving https://doi.org/doiRA/10.5240/B1FA-0EEC-C316-3316-3A73-L will
return: \[ { "DOI": "10.5240/B1FA-0EEC-C316-3316-3A73-L", "RA": "EIDR" }
\] A full list of RA names and abbreviations can be found on the web
site. Possible error states include "Invalid DOI", "DOI does not exist"
and "Unknown".

DOI HANDBOOK 63 Chapter 6

DOI APPLICATIONS

This chapter discusses some of the ways in which resolution can be
harnessed to provide applications with the ability to resolve a DOI name
to the most appropriate content chosen from multiple DOI resolution
options. These options can include pop-up menus offering manual
selection, and consistent automated selection through content
negotiation and Linked Data.

In This Chapter 7.1 Introduction to DOI Applications
................................................. 65 7.2 Use and
Extension of the Resolution Functions ............................ 65
7.3 Applications of the 10320/LOC Element
...................................... 65 7.4 Redirection to Linked Data
Servies ............................................. 68 7.5 Dynamic
Identification of the Fragments of an Entity ..................... 69

DOI HANDBOOK 64 7.1 INTRODUCTION TO DOI APPLICATIONS In order to
maintain a persistent identifier, an active management service in
collaboration with registrants is required. To justify that management
service, a DOI application normally provides more value than simply
registering a DOI --- typically a Registration Agency offers an added
value service, such as citation linking or metadata management. DOI
names can identify many types of referent, and may resolve to more than
just a permanent, indirect link to that referent (or a proxy for the
referent). They can also provide or point to any useful information
about the object when that information has been provided by the
registrant or a third party. This information can include any type of
descriptive metadata and any type of service related to the object, such
as rights clearance, alerting services, data visualization or any other
associated information or service. The information can be used in many
ways by DOI applications customized to meet users' needs. NOTE No
ability to search from metadata to DOI name (reverse look-up) is
provided by the DOI System. It may be offered by Registration Agencies
or other services as a value-added feature. A variety of technologies
are in use for this purpose among the RAs, including the Cordra registry
system as well as custom applications.

7.2 USE AND EXTENSION OF THE RESOLUTION FUNCTIONS At the most basic
level, all DOI applications query the DOI System by resolving a DOI
name. The request can be structured to ask for all of the DOI record
elements associated with that DOI name, or all of the elements of a
specific type and/or index, etc. (see DOI Proxy Query Command Format).
Applications are built to understand one or more of the element types,
and parse, evaluate, and take action based on the corresponding element
values. The DOI record that is associated with a DOI name is stored in
the DOI System in type/value pairs (see 5.1.2). This is extremely
flexible and open: new types can be added at any time, and the values
can be of arbitrary complexity. Type/value pairs can be administrative
(creation date, permissions, etc.), well known and standardized (URL,
email, 10320/LOC, etc.), or created by a Registration Agency for a
specific application purpose (for example, a custom type with a value
that is binary data or a specially formatted string). There can be many
type/value pairs associated with a DOI name, and multiples of the same
type. Associating XML, or other machine readable data with a DOI name,
expands the utility of multiple resolution even further, adding
features, and offering more op-tions for negotiating content, and
facilitating the creation of Linked Data applica-tions. NOTE New types
should, but are not required to, be registered in the Handle System as
Handles. As a general rule types containing a slash (for example,
10320/LOC) should be considered full Handles and those without a slash
(for example, URL) should be assumed to be suffixes under the 0.TYPE
prefix (with the previous example: 0.TYPE/URL). The type Han-dle Record
may define the syntax, structure, possible semantics, or any other
necessary descriptive characteristics of the corresponding value field.
For more information, see the Digital Object Identifier Resolution
Protocol (DO-IRP) Specification.

7.3 APPLICATIONS OF THE 10320/LOC ELEMENT The 10320/LOC element can be
used if multiple resolution is required.

7.3.1 CHOOSE-BY MECHANISM Multiple resolution with 10320/LOC element
(see 5.4.2) is useful for building applications where the required
evaluation is to choose from a set of possible outcomes based on some
criteria. An application developer could DOI HANDBOOK 65 create a type
in which to store values used by a client to generate a menu of options
for a user when the user resolves a DOI name. In the case of a document,
the user might be given the option to view the document, view document
metadata, share the document by emailing the URL to an associate, visit
the author's blog, etc. For a dataset, the choices offered to the user
on the landing page may include viewing the com-plete dataset, viewing
only selected data, or some other choice of interaction with the dataset
based on the information made available to a client via resolution of
the DOI name. For example, scholarly journal articles are assigned one
DOI name, but they can be available from multiple web sites, and readers
may wish to download an article from a service to which they are
subscribed. Crossref uses multiple resolution to enable users to resolve
an article's DOI name, and choose which version of an article they wish
to view, as illustrated below.

Figure 19 Choose-by mechanism example

7.3.2 AUTOMATED SELECTION OF A URL ACCORDING TO VARIOUS CRITERIA
Multiple resolution with 10320/LOC element (see 5.4.2) can be used to
enable a DOI resolver to choose what the outcome of resolving a DOI name
will be for a specific user, based on a given criteria. The figure below
shows (non-administrative) elements associated with DOI name
10.1525/bio.2009.59.5.9. When this DOI name was registered it had a
single URL element (type of URL and value, aka data, equal to a JSTOR
URL). A 10320/LOC type was added to provide instructions for offering
other resolution options (see 10.4.1 for information about the XML
attributes used in 10320/LOC element). When this record is returned to
the DOI Proxy, it recognizes the 10320/LOC type and, if asked to do so,
performs an evaluation of the location values based on a given criteria.

DOI HANDBOOK 66 Figure 20 10320/LOC example The DOI Proxy may be
required to (see also 10.2): • ignore type 10320/LOC In that case, the
DOI Proxy would resolve 10.1525/bio.2009.59.5.9 and select the URL value
https://www.jstor.org/stable/25502450. This action would be per-formed
by any DOI resolver not knowing the type 10320/LOC. • resolve
10.1525/bio.2009.59.5.9 and return to the user both of the URLs in the
cr_type attributes in the 10320/LOC value, letting the user choose the
next ac-tion (choose-by mechanism) • resolve
10.1525/bio.2009.59.5.9?locatt=country:gb In that case, the DOI Proxy
would determine the user's geographic location from their IP address. It
would then select the URL https://www.bioone.org/doi/ DOI HANDBOOK 67 
full/10.1525/bio.2009.59.5.9 for users in the UK ("gb" code), and would
perform a random selection for all others. • resolve
10.1525/bio.2009.59.5.9?locatt=id:1 In that case, the Crossref metadata
service at https:// mr.crossref.org/iPage?doi=10.1525%2Fbio.2009.59.5.9
would be selected.

7.4 REDIRECTION TO LINKED DATA SERVIES Linked Data is the general term
for a set of best practices for exposing data in machine-readable form
using the content-negotiation feature of the standard HTTP(S) web
protocol. These best practices support the development of tools to link
and make use of data from multiple web sources without the need to deal
with many different proprietary and incompatible application programming
interfaces (APIs), and use of HTTP(S) to request data in structured form
meant for machines instead of human-readable displays. In Linked Data
applications, evaluation of the HTTP(S) request that comes in to the
proxy service determines if it is a request for content of form
application/rdf+xml, or one of a few similar types that are commonly
understood to be a request for Linked Data. These requests for special
content types would come from automat- ed processes or special "linked
data" browsers and would not normally come from end users. The utility
of this, of course, is that it allows outside developers to query the
extensive and reliable set of metadata records held by Registration
Agencies (RA) to build value-added services. Some RAs are using this
approach for all of their DOI names, offering services that return
metadata in a common machine-readable format. A significant advantage of
applying Linked Data principles and technologies to DOI-registered
material is that it is "data worth linking to": it is curated,
value-added, data, which is man-aged, corrected, updated and
consistently maintained by RAs. It is also persistent, so avoiding
"bit-rot". In practice, the quality of Linked data implementations is
only as good as the data you are linking to, and the meaning and
contextualization of the link you use. The DOI System can offer "curated
data", it means consistent, managed, linking so you can link to other
"quality data" with confidence, while still using the standard Linked
Data technologies. The following figure shows a redirection to the
metadata service managing the DOI name. The 10320/LOC element
information can be stored at prefix level (see 10.4.3): should an RA at
some point need to change their approach to linked data and point to a
different service or use different parameters, the change could be made
to a single DOI prefix and it would apply to all of the millions of DOI
names automatically.

DOI HANDBOOK 68 Figure 21 Dynamic building of a web page enriched with
metadata For more information, see 5.4.4.

7.5 DYNAMIC IDENTIFICATION OF THE FRAGMENTS OF AN ENTITY In some cases,
applications may require the identification of fragments of an entity,
rather than the full entity. Each such fragment may be assigned a
separate DOI name if it is practical and useful to do so (for example,
if a specific table within a book is likely to be re-used many times).
However, this may not always be possible: there are also cases where one
wishes to identify in principle any fragment of this entity as it
becomes needed on the fly. For such cases, use may be made of Template
Handles (see section 11 in the Handle.net Technical Manual ): a single
template DOI Handle can be included in the form of a base formula that
allows any number of extensions to that base to be resolved as full DOI
Handles, according to a pattern, without each such Handle being
individually registered. This would allow, for example, the use of DOI
names to reference an unlimited number of ranges within a video without
each potential range having to be registered with a separate Handle. If
the pattern needs to be changed, for example, the video moves or a
different kind of server is used to deliver the video clips, only the
single base DOI name (Handle) needs to be changed to allow an unlimited
number of previously constructed extensions to continue to resolve
properly.

DOI HANDBOOK 69 Chapter 7

DESIGNING AND DEVELOPING A DOI APPLICATION

This chapter assists business analysts and developers in designing and
developing applications based on the DOI System. Before starting the
design or development of a DOI application, you should have read the
previous chapters of the Handbook. See also 10.6.

In This Chapter 8.1 Checklist for Designing a DOI Application
.................................... 71 8.2 Design Considerations
............................................................. 72 8.3
Defining an Identifier Scheme
.................................................... 73 8.4 Managing
System Metadata Models ........................................... 74
8.5 Developing a DOI Resolver
....................................................... 74 8.6
Configuring the Resolution Error Message Handling ......................
75

DOI HANDBOOK 70 8.1 CHECKLIST FOR DESIGNING A DOI APPLICATION The DOI
System has the flexibility to meet identification and resolution
requirements of any application domain. However, these don't come "in a
box": someone needs to build the specific social and technical
structures to support the particular requirements of a community, and
provide applications which offer value to that community. In designing a
DOI System application several questions need to be considered. Table 3
Checklist for designing a DOI application Question Description See

What are we identifying with this The rules about what is identified,
identifier? and whether two things being identified are "the same
thing", are made at the level of a specific application of the DOI
System, and this is a role of Registration Agencies (RA). This
deceptively easy question (usually known as "granularity") is one of the
most diffi-cult encountered in all discussions about identifiers (but
the one most commonly overlooked) and an answer is often much more
difficult than it might at first appear. The answer to when two things
are "the same thing" is entirely contextual, it means what a specific
application will need to distinguish.

What are we resolving to from this A DOI name can resolve to Chapter 5
identifier? anything. At minimum, it will resolve to a URL, but there
may be multiple URLs or it can be configured to return multiple other
data types.

What metada-ta are we Without an explicit structured Chapter 4
associating with this DOI name? metadata layer, an identifier
essentially can have no meaning at all outside a specific application.
Most DOI names are not yet used for wide-spread interoperability, but
are used within specific applications. They do not need to reveal
explicit structured metadata, but RAs maintain System Metadata and
additional DOI HANDBOOK 71  Question Description See

                                        metadata which may be delivered
                                        in a number of ways.

What are the interoperabil-ity The DOI System has a 4.4 requirements?
mechanism for interoperability with other standards. If the application
is in a sector where other identifiers or metadata schemes are already
in use, an RA will need to work out an implementation of this in detail
that is practical for the community that they serve.

How will the DOI application be A cost is associated with 2.2.2 paid
for? managing persistence and with assigning identifiers and data to
ensure long-term stability, because of the need for human intervention
and support of an infrastructure. In the DOI System the way in which
these costs are recouped depends on the application. RAs are free to
establish their own business model for the allocation of DOI names. The
services offered by a DOI RA will include more than simple provision of
a DOI name: these value added services may include data, content or
rights management. There is no single business model applicable to all
DOI RAs (and consequently no single answer to the question of how a DOI
name is paid for and what it costs).

8.2 DESIGN CONSIDERATIONS Flexibility and scalability are important
features of well-designed DOI-enabled services. The most flexible and
scalable approach is to use the DOI System as a lightweight redirection
mechanism, resolving identifiers to well-structured data. This approach
can be used to provide DOI-related services beyond that of a single
level of redirection. In addition to simply resolving a DOI name and
getting back a single URL, DOI registration agencies may offer multiple
resolution services, linking a DOI name to multiple options

DOI HANDBOOK 72 about the referent (for example, bibliographic
metada-ta), and those options may include requests for particular
representations of metadata, or metadata useable only for particular
contexts Developers may choose to put all or most of the information
provided by the service in the DOI System itself, such that the DOI
system is the primary service provider, or alternatively, use the DOI
System to point to one or more external services to provide the desired
information and functions. For example, the DOI System may be used to
store all of the data required to display a simple menu of labelled
options for a user to pick from, but redirecting to an external service
that stores large quantities of scientific data for visualization tools,
or multiple image files, might be preferable to storing that data in the
DOI System. Developing applications that store, use, and share
high-quality machine-readable data in a standardized format is a further
design consideration. DOI applications can be designed to conform to the
best practices of Linked Data, a well-known concept of exposing data in
machine-readable form, using the content negotiation feature of the
standard HTTP web protocol. NOTE The use of HTTPS over HTTP is highly
recommended. Creating services that take advantage of DOI structured
data to create consistency across RA applications is encouraged.
Collaboration is encouraged whenever possible. Third party application
developers not part of the DOI Foundation are also encouraged to be part
of the process of creating services that take advantage of DOI
structured data. A sampling of DOI application services based on
multiple resolution and content negotiation are described in Chapter 6.
New services may be created at any time. Questions can be sent to
info@doi.org.

8.3 DEFINING AN IDENTIFIER SCHEME If you need to define a new identifier
scheme, consider the following: • Avoid re-inventing the wheel: if it
appears that you need to devise a new identifier scheme, examine whether
the problem can be avoided by re-using existing identifiers. • If a new
scheme is needed, consider if an existing protocol or identifier
registry can be harnessed to implement your scheme. • Register your
scheme with an appropriate public namespace declaration. • Provide easy
links for semantic mapping by specifying a well-formed metadata scheme
and publishing it. • Consider the community and business implications
for others who may need to use your scheme • Provide clear guidance on
rights and obligations of use of your scheme. • Adopt identifiers with a
mechanism for ensuring persistence.

8.3.1 INTEGRATING ANOTHER IDENTIFIER SCHEME Where syntax rules permit
the incorporation of an existing identifier from another scheme as part
of the DOI name, such rules shall not form part of ISO 26324. In such
cases, attention is drawn to the following points. • The same referent
shall be denoted by both the DOI name and the included identifier
string, to the degree that is necessary to distinguish it as a separate
entity within each identifier scheme. • Within the DOI System itself,
the DOI name is an opaque string. No definitive information relating to
the other identifier scheme should be inferred from the specific
character string used for a DOI name, and the DOI name is not guaranteed
to be usable in any non-DOI applications designed for the other
identifier scheme. • Specific syntax rules for the incorporation of an
existing identifier from another scheme shall be maintained by the ISO
26324 Registration Authority.

DOI HANDBOOK 73 8.4 MANAGING SYSTEM METADATA MODELS Models are used to
specify System metadata (see 4.3). You may want to build on existing
models or create new ones.

8.4.1 CREATING OR UPDATING A METADATA MODEL Authority to make changes in
the existing DOI models lies with the Metadata Working Group. Any member
of the DOI Community may make proposals for updates to a model, or for
introducing a new part of a model, at any time. Implementing the changes
will be the responsibility of the DOI Foundation's selected technical
provider. The procedure for making changes to the DOI System model is
defined in the Metadata Working Group - Processes and Responsibilities
document. NOTE RAs wishing to develop de novo schemes and new metadata
applications are also encouraged to contact the DOI Foundation for
advice.

8.5 DEVELOPING A DOI RESOLVER For your DOI application, you may use the
DOI Proxy (see 5.3.1). Additional DOI resolvers can be built and
additional methods can be used to access the core DOI name resolution
system without interfering in any way with the ongoing operation of the
DOI Proxy. For example, you may: • set up your own web-to-DOI-name proxy
server • use the DO-IRP protocol to query the DOI System directly: see
7.5.1 • use the DOI REST API to access to DOI name resolution services
using HTTPS: see 5.3.3 NOTE The resolution functionality might also be
delivered to a browser by means of a scripting feature, such as
JavaScript. However, this method is not recommended since languages are
likely to evolve faster than protocols. As resolution is freely
available, you can develop your DOI resolver entirely independently of
the DOI Foundation, but we encourage developers to let us know about
their applications in order that we may: let others know about it if it
is public; work with developers to improve their understanding of the
DOI System and thus the success of their efforts.

8.5.1 DEVELOPING HANDLE SYSTEM CLIENT SOFTWARE An organization or
individual developing Handle System client components is encouraged to
use the CNRI client software and the standard interfaces supplied with
it: the Handle.Net® Software Client Library Java™ Version is freely
available and can be used to develop new resolution clients as needed,
either for individual applications or for use in completely separate
systems. In particular, the Handle System client shall not interfere
with the normal operation of a Local Handle Service (LHS) or other
client applications in interacting with the Handle System client
software or the GHR (see 5.1). In the event an organization or
individual wishes to use its own interface software, it is their
responsibility to ensure that these inter-faces remain compatible with
the current Handle System interface specification. NOTE The
net.handle.apps.simple package has a number of examples of how to use
the Handle client library. Contact the Handle.Net Registry Administrator
at hdladmin@cnri.reston.va.us for information.

DOI HANDBOOK 74 8.6 CONFIGURING THE RESOLUTION ERROR MESSAGE HANDLING
Actions which result in an attempted resolution not being successful
result in error messages. These can be provided by Registration Agencies
(RA), or by the DOI System centrally. RAs may use similar wording and
procedures in their own services as the DOI System. In addition, an RA
can request the DOI technical support service provider to configure the
DOI Proxy to report a "DOI Name Not Found" error message to you in case
the entered prefix is your prefix. See 5.4.5.

DOI HANDBOOK 75 Chapter 8

DEFINING RA AND REGISTRANT POLICIES

The DOI Foundation defines high-level operational policy and assigns the
execution of this policy to the Registration Agencies (see 2.3). The
Registration Agencies enforce their own operational policies, specific
to their community of interest. These specific policies will be
consistent with the DOI Foundation's high-level policies. This chapter
assists the Registration Agencies or registrants in defining their own
policies.

In This Chapter 9.1 Defining a Prefix Allocation Policy
.............................................. 77 9.2 Defining a Data
Maintenance Policy ........................................... 77 9.3
Defining a DOI Name Registration Policy
.................................... 77

DOI HANDBOOK 76 9.1 DEFINING A PREFIX ALLOCATION POLICY As a
Registration Agency (RA), you may choose to assign prefixes to your
customers (see 1.7.4). To do so, you should define a prefix allocation
policy. The DOI Foundation allots to each RA prefixes as a block of
sequential numbers that have no special meaning (prefixes are created by
the DOI technical support service provider). No reserved prefixes may be
requested. Some RAs will manage all assignments themselves and can
operate under a single prefix. Others will want to delegate assignment
to customers and in this case, it is recommended that prefixes are
assigned at an appropriate level to deal with business requirements.
Typically, a Registration Agency (RA) may issue one prefix per customer,
but it might also be appropriate to issue a prefix per brand, or to some
recognizable cluster of products (for example, a publisher imprint). The
choice is the RA's, but the DOI Foundation and/or other RAs can discuss
requirements and make recommendations. NOTE In case DOI names must be
transferred from one RA to another, the foremost technical issue in this
transfer is the one-to-one relation of prefix to Local Handle Service
(LHS). In this perspective, RAs should allocate at least one separate
prefix for each customer, and where appropriate more than one, since the
fundamental constraint is that all DOI names under a given prefix must
reside in the same LHS (this general architecture is a logical and
efficient approach to a distributed service and is far from unique to
the Handle System).

9.2 DEFINING A DATA MAINTENANCE POLICY The effective operation of the
DOI System depends on accurate resolution of a DOI name to the
appropriate URL or other data type. To maintain quality services, it is
also crucial that metadata assigned to a DOI name be regularly updated.
Therefore, the maintenance of URLs and data about a DOI name should be
subject to a policy. In particular, the policy should specify who,
between the Registration Agency (RA), the registrant or a service
organization acting with the authority of the registrant, is responsible
for the data maintenance.

9.3 DEFINING A DOI NAME REGISTRATION POLICY You must define a policy
which specifies: • that all DOI names must be registered in the DOI
Directory (see 5.2) • who, between the Registration Agency or the
registrant, generates the DOI names • the general scheme of the suffix
to be followed, if any (for example, if another identifier scheme is
integrated in the DOI name syntax) • the rules governing the suffix
syntax (see also 3.3) with possible constraints from outside the DOI
System on the suffix, for example: • on the character set: see • on the
suffix length • etc

DOI HANDBOOK 77 Chapter 9

OPERATING AND MAINTAINING THE RA SERVICES

This chapter assists the Registration Agency's service operations team
in perform-ing service operation tasks.

In This Chapter 10.1 Defining Operational Processes
............................................... 79 10.2 Managing the
User Accesss Rights .......................................... 79 10.3
Issuing Prefixes to Registrants
................................................. 79 10.4 Maintaining
the Resolution Services ......................................... 79
10.5 Operating Your Own LHS
....................................................... 80 10.6
Transferring DOI Names from One Registrant to Another ............. 81
10.7 Transferring DOI Names from One Registration Agency to Another
........................................................................................................................
81

DOI HANDBOOK 78 10.1 DEFINING OPERATIONAL PROCESSES This section
describes a DOI name registration process workflow example. NOTE If you
want to allow DOI name administration from a local web server, you may
use CNRI's net.handle.apps.admin_servlets. Contact the Handle.Net
Registry Administrator at hdladmin@cnri.reston.va.us for information.

10.1.1 DEFINING THE DOI NAME REGISTRATION PROCESS Registration Agencies
(RA) support registration of DOI names with an associated metadata
declaration. Individual RAs develop their own workflow and procedures
for the management of DOI name registration, and metadata registration
and maintenance, and provide their own information to their community of
registrants. The service provided by each RA must include quality
assurance measures, so that the integrity of the DOI System as a whole
is maintained at the highest possible level (delivering reliable and
consistent results to users). This includes ensuring that the DOI record
is accurate and up-to-date and that the System Metadata is con-sistent
and complies with appropriate DOI data model standards. The general
steps of the DOI name registration process are: 1. The registrant sends
to the RA data of DOI names to be registered. 2. The RA creates the DOI
names by registering them in the Handle System. 3. The RA adds the
appropriate registrant data to their metadata service. 4. The RA sends
to the registrant the registration process results.

10.2 MANAGING THE USER ACCESSS RIGHTS Each Registration Agency
administers the access rights and permissions for the DOI name
registrants that form their community. They must provide adequate
security to ensure that only the registrant (or someone acting with the
registrant's permission) is able to maintain both metadata and DOI
record data. For information about the user access right management in
the Handle System, see the Digital Object Identifier Resolution Protocol
(DO-IRP) Specification.

10.3 ISSUING PREFIXES TO REGISTRANTS An authorized Registration Agency
issues prefixes to registrants where relevant and requests the DOI
Directory Manager to register such new prefixes in the Handle System.
The RA maintains the systems environment for storing a minimum set of
descriptive metadata that can be provided and may be integrated with the
Handle System.

10.4 MAINTAINING THE RESOLUTION SERVICES The Registration Agency (RA) is
responsible for taking the necessary steps to ensure the proper
maintenance of their DOI prefixes and DOI names, including the
following: • An administrator must be designated for each prefix (or set
of prefixes): the pre-fix administrator can create DOI names under their
prefix. The DOI technical support service provider also maintains
administrative permission for the prefix. This is intended as backup for
administration. Note that the creation of derived prefixes can only be
done by the technical support service provider.

DOI HANDBOOK 79 NOTE The technical support service provider configures
the prefix administrators in the prefix Handle (see 10.5). • Secure
maintenance of private keys must be ensured by each administrator. •
Service configuration changes must be timely reported to the DOI
technical support service provider. • The RA must inform the technical
support service provider and the DOI Foundation in the event of any
major operation on the DOI names that could possibly interrupt the
mirroring mechanism. • Additional requirements apply to RAs who operate
their own LHS: see 9.5.3.

10.4.1 TROUBLESHOOTING RESOLUTION PROBLEMS The DOI technical support
service provider provides technical and operational support for the DOI
System as a contractor. Further details of the relevant Agreement for
Technical Services are available to potential and current Registration
Agencies. If you receive an error message forwarded by the DOI technical
support service provider, you must take the appropriate action. See the
handling of resolution errors in the DOI System in 5.4.5.

10.5 OPERATING YOUR OWN LHS If a Registration Agency (RA) chooses to
implement and operate a Local Handle Service (LHS) for their DOI names
(see 5.2.2), the DOI technical support service provider will provide the
RA with the necessary technical guidance to help them install and
administer their LHS. The technical support service provider is
responsible for the scalability of the system and, in consultation with
the DOI Foundation, for implementing future developments leading to its
growth and any improvement to its technical sophistication.

10.5.1 INSTALLING THE LHS For information about the LHS installation,
see Handle.Net Technical Manual. The installation process will create a
file called sitebndl.bin that will contain the service information for
the LHS. As per the instructions in the distribution, you will need to
send the file to the DOI technical support service provider at
doi-admin@doi.org. Name, organization name, and the fact that the
request is com-ing from a DOI RA is important so that the technical
support service provider knows to create prefixes that begin with 10.

10.5.2 SETTING UP THE LHS You are responsible for modification of the
configuration of your LHS to allow a secondary server installation at
the DOI technical support service provider. The secondary server will
house a complete database of the your DOI names. This re-quires a minor
change in the server's configuration file. This will be coordinated by
the technical support service provider. After setup is complete a
regularly execut-ing task (for instance, a cron job) will be created to
check to see if the secondary server is able to connect to your server.
If there is problem with the connection (for example, your server is
shut down) you will be notified by email and expected to correct the
problem as soon as possible For more information about LHS setup, see
Handle.Net Technical Manual.

10.5.3 LHS OPERATION REQUIREMENTS Maintaining overall integrity of the
Handle System entails ensuring that each of the following conditions is
met by administrators, who must agree to operate their resolution
services during the period while the authorization is in effect. The
term "system" as used below refers to those components run by each
administrator, and the DOI HANDBOOK 80 interaction of these components
with the Global Handle Registry (GHR) and the users of the Local Handle
Service (LHS). Operational goals for administrators in-clude: • Ensuring
compatibility and smooth interaction among system components •
maintaining consistency and reliability in service performance •
conducting proper system management and performance tracking • offering
non-interrupted access to the GHR • taking adequate system security
measures

It is also the responsibility of the Registration Agency to inform the
DOI technical support service provider of any configuration changes in
their LHS. NOTE A number of utilities for low-level maintenance of a
Handle server are available such as net.handle.apps.tools and
net.handle.apps.site_tool. Contact the DOI tech-nical support service
provider at doi-admin@doi.org.

10.6 TRANSFERRING DOI NAMES FROM ONE REGISTRANT TO ANOTHER If a
compilation of multiple assigned DOI names (for example, a journal
containing a collection of articles; an imprint; a recording catalogue;
etc.) is transferred from one registrant to another (both registrants
being related to the same Registration Agency (RA)), the DOI names
within that compilation are transferred as well. Each RA will develop
appropriate procedures for proper transfers. Transfers may be a sale, or
any form of exchange, commercial or otherwise. If the new owner is not
already a registrant, special arrangements may have to be made
appropriate to the case. Consult the DOI Foundation for guidance if
necessary. The individual DOI names stay the same, it means that what
the DOI name identifies is not changed. This is a fundamental
requirement. The DOI name prefix does NOT change (recall that a prefix
is not meaningful, but is initially assigned to a reg-istrant for
convenience in generating DOI names only; no reverse look-up can be
inferred to a prefix). The administrative value is changed in order for
the new owner to modify its data elements (most likely the URL element).
Both registrants involved in the transfer need to send email to the DOI
technical support service provider at doi-admin@doi.org giving
permission for the transfer. The technical support service provider will
assist RAs to ensure an efficient and successful outcome.

10.7 TRANSFERRING DOI NAMES FROM ONE REGISTRATION AGENCY TO ANOTHER
Moving an entire prefix worth of DOI names from one Registration Agency
(RA) to another is easy. Splitting control of a prefix between two
administrative bodies who both use the same Handle service (it means,
when it has not been possible to foresee a split by issuing separate
prefixes) is also possible but more complex. In general, there are two
solutions: 1. leave it with one or the other service (or the DOI default
Handle service run by the DOI technical support service provider on
behalf of the DOI Foundation) and split up the administration, such that
the managers of one service allowed the 'foreign' admins access 2. alias
all the DOI names under the old prefix to DOI names under a new prefix
controlled by the new RA The old DOI names do not have to be maintained
other than ensuring resolution to the new DOI names All of the above is
strictly from a DOI System point of view and does not address any
internal workflow issues or value-added services that the RAs provide
that in-teract with Handle administration, which would of course be
specific to the RA.

DOI HANDBOOK 81 Chapter 10

APPENDIX

In This Chapter 11.1 System Metadata Model
......................................................... 83 11.2 DOI
Proxy Query Command Format ......................................... 85
11.3 DOI REST API Request and Response Formats .........................
86 11.4 10320/LOC Element
............................................................... 89 11.5
Prefix Handle Example
........................................................... 94 11.6
System Tools
........................................................................
95

DOI HANDBOOK 82 11.1 SYSTEM METADATA MODEL The DOI System Metadata Model
specifies the DOI System Metadata data elements and allowed values of
the metadata model. It is maintained by the DOI Foundation. It consists
of two parts: • DOI Schema • DOI Schema AVS (Allowed Value Sets) The
procedure for making changes to the DOI System model is defined in the
Metadata Working Group - Processes and Responsibilities document.

11.1.1 DOI SYSTEM ELEMENTS This section describes the elements of the
DOI System Metadata. These descriptions are based on the extensible
model contained in ISO 26324. DESCRIPTIVE ELEMENTS The table below lists
the descriptive elements used in DOI System Metadata. Table 4 System
Metadata: descriptive elements System element Occurs Description

DOI name 1 Specific DOI name allocated to the identified referent.

alternateIdentifier(s) 0-n Other identifier(s) referencing the same
referent if available. This element contains a type element appropriate
to the referentType.

referentName(s) 1-n Name(s) by which the referent is usually known
(example: title). This element contains a type element appropriate to
the referentType. This element also contains a language element, for
which the allowed value list is the ISO 639-2 code list.

referentType 1 The general type of the referent (examples: creative
work, party, event). This is an open list

DOI HANDBOOK 83  System element Occurs Description

                                                                       FOOTNOTE             Registration
                                                                       Agencies can request the addition
                                                                       of new allowed values to open lists
                                                                       (see 4.3.4).

referentSubType 1 Specific type of the referent as used by registration
agen- cies to enumerate things to which a DOI name is registered. This
list is maintained at https:// doi.org/10.1000/282. This is an open list
FOOTNOTE Registration Agencies can request the addition of new allowed
values to open lists (see 4.3.4).

relatedIdentifiers 0-n This element is only considered part of the
System Metadata if it is necessary to dereference the related Identifier
in order to access descriptive metadata for the referent. This element
contains a role element, which is an open list for which new allowed
values may be registered.

basicMetadata 1 Metadata sufficient to define what the referent is.
Fields necessary will depend on the Referent Type and Sub-Type.

The data model is maintained at https://doi.org/10.1000/282.
ADMINISTRATIVE ELEMENTS The table below lists the administrative
elements used in DOI System Metadata. Table 5 DOI System: administrative
elements System Metadata element Occurs Description

registrationAuthorityCode 1 Code assigned to denote the name of the
agency (authorized by the ISO 26324 Registration DOI HANDBOOK 84  System
Metadata element Occurs Description

                                                                           Authority) that is-sued this DOI
                                                                           name.

issueDate 1 Date when this DOI name was issued.

11.2 DOI PROXY QUERY COMMAND FORMAT The format of a resolution query
command to the DOI Proxy (see 5.3.1) is as follows:
https://doi.org/`<doi-name>`{=html}?`<param_1>`{=html}&`<param_2>`{=html}&..
where: • `<doi-name>`{=html}: Percent-encoded DOI name (see 3.8) to be
resolved • `<param_i>`{=html}: parameter i passed to the DOI Proxy
Example: https://doi.org/10.1000/1?noredirect&type=URL NOTE HTTP instead
of HTTPS still supported (but not recommended). The following table
lists the native parameters supported in a query sent to the DOI Proxy.
(Other parameters may be passed through the proxy using the urlappend
parameter.) Table 6 DOI Proxy: query parameters Parameter Description
See

noredirect Do not redirect using URL or 10320/loc type elements. Display
the elements instead.

ignore_aliases Ignore HS_ALIAS elements. The HS_ALIAS element is used to
specify a Handle that should be resolved instead of the input Handle.

auth Authoritative query. The DOI Proxy bypasses its cache and sends its
resolution request to an authoritative Handle service (it means to a
primary service, not to a mirror service).

DOI HANDBOOK 85  Parameter Description See

cert Certified query. The DOI Proxy requires an authenticated response
from the Handle service (it means that the DOI Proxy asks the Handle
service to sign its response and the Proxy will check the signature
before accepting it).

in-dex=`<value>`{=html} Resolve the DOI record element 5.1.2 at the
specified index value and do not resolve the other elements except if
otherwise required. May be repeated to resolve multiple indexes.

type=`<value>`{=html} Resolve the DOI record element 5.1.2 of the
specified type value and do not resolve the other elements except if
otherwise required. May be repeated to resolve multiple types.

urlap-pend=`<value>`{=html} Append the value of this parameter to the
end of the URL used for redirection

locatt=`<key>`{=html}:`<value>`{=html} In case of a multiple resolution:
5.4.2 use this key:value pair for the in-terpretation of the 10320/LOC
element.

action=showurls In case of a multiple resolution: 5.4.2 return an XML
representation of the possible redirect locations stored in the
10320/LOC element.

All combinations of parameters are accepted (not all are useful). For
example, if the index and type query parameters are used together then
any element which matches any of the specified indexes or types is
returned.

11.3 DOI REST API REQUEST AND RESPONSE FORMATS The DOI Proxy REST API
allows programmatic access to DOI name resolution using HTTP(S).

DOI HANDBOOK 86 11.3.1 REST API REQUEST FORMAT A REST API request can be
made by performing a standard HTTPS GET of
/api/handles/`<doiName>`{=html}:
https://doi.org/api/handles/`<doiName>`{=html}?`<param_1>`{=html}&`<param_2>`{=html}&..
where: • `<doiName>`{=html}: percent-encoded DOI name (see 3.8) to be
resolved • `<param_i>`{=html}: parameter i passed to the DOI Proxy REST
API

Example:
https://doi.org/api/handles/10.1000/1?type=URL&callback=processResponse
The table below lists the parameters supported in a query sent to the
DOI Proxy REST API. Table 7 DOI API query parameters Parameter
Description

callback Use JSONP callback (instead of CORS headers).

pretty Pretty-print the JSON output.

auth Authoritative query. The DOI Proxy bypasses its cache and sends its
resolution request to an authoritative (primary) Handle service.

cert Certified query. The DOI Proxy requires an authenticated response
from the Handle service (it means that the DOI Proxy asks the Handle
service to sign its response and the Proxy will check the signature
before accepting it).

index Resolve the DOI record element at the specified index and do not
resolve the other elements except FOOTNOTE The index and type query
parameters if explicitly required. May be repeated to resolve can be
used together: any element which match-es multiple indexes. any of the
specified indexes or types is returned

type Resolve the DOI record element of the specified type and do not
resolve the other elements except FOOTNOTE The index and type query
parameters if explicitly required. May be repeated to resolve can be
used together: any element which matches multiple types. any of the
specified indexes or types is returned

DOI HANDBOOK 87 11.3.2 REST API RESPONSE FORMAT The REST API response is
a JSON object which includes a response code, an echo of the resolved
Handle identifier, and either a list of DOI record elements or, in the
case of an error, an optional message which is a string describing the
error. The figure below shows a response example.

Figure 22 REST API response example RESPONSE CODE The response code is
an integer referring to a Handle System protocol response code. The most
common response code values are: • 1 : Success. (HTTP 200 OK) • 2 :
Error. Something unexpected went wrong during DOI name resolution. (HTTP
500 Internal Server Error) • 100 : Handle Not Found. (HTTP 404 Not
Found) • 200 : Values Not Found. The Handle Record exists but the
required elements do not exist. ELEMENT DATA An element consists of: •
an index (an integer): unique element identifier inside the Handle
Record • a type (a string): for example, URL, description, IP address,
email address, etc. • a value (a data object): see table below • a Time
To Live (TTL; an integer, or, in the rare case of an absolute expiration
time, an ISO8601-formatted string): specifies how long the element value
can be cached before the information source should again be consulted

DOI HANDBOOK 88 The table below describes the "value" property depending
on the "format" property of the element data object. For more
information about HS_ADMIN, HS_VLIST and HS_SITE data, see Digital
Object Identifier Resolution Protocol (DO-IRP) Specification. Table 8
Element value ("data" object) "format" property "value" property

"string" Is a string representing the data as a UTF-8 string.

"base64" Is a string, with a BASE64 encoding of the data.

"hex" Is a string, with a hex encoding of the data.

"admin" Is an object representing an HS_ADMIN element (Handle
administrator) with the properties: "handle": identifier of the Handle
used to identify the administrator "index": index of the element in the
administrator's Handle Record storing the administrator's public key
"permissions": access rights to the Handle Record granted to the
administrator

"vlist" Is an object representing an HS_VLIST element (refers to a list
of administrators (public keys in Handle Records)).

"site" Is an object representing an HS_SITE element (Handle service site
information).

11.4 10320/LOC ELEMENT This section contains details about the 10320/LOC
element used in the multiple DOI resolution (see 5.4.2).

11.4.1 10320/LOC: XML ATTRIBUTES The 10320/LOC type is used in a DOI
record to describe complex location selection rules in XML format. The
following table lists the XML attributes supported in these rules.

DOI HANDBOOK 89 Table 9 10320/loc: XML attributes Attribute Description
Mandatory

choose-by Identifies a comma-delimited list No of location selection
methods: the DOI resolver will iterate over the selection methods in the
specified order. For each applied selection method: If one and only one
location is selected then the DOI resolver will redirect to this
location. Otherwise, the DOI resolver will apply the next selection
method. If no selection method is left then the DOI resolver will apply
the weighted method which guarantees to return a single location. If no
chooseby attribute is specified then the default
("locatt,country,weighted") is assumed. Possible location selection
methods: locatt: Only locations from an attribute passed in the
Proxy/DOI name-URL link are selected. Example: With doi:10.123/456?
locatt=id:1, the resolver will return the locations that have an "id"
attribute of 1. country: Only locations that have a country attribute
matching the country of the requester are selected. If no matching
locations are found then locations that have no country attribute are
selected. Note: The https://hdl.handle.net and https://doi.org Proxies
de- termine the country of the requester using a GeoIP lookup. weighted:
A single location is selected based on the weight assigned to each
location:

DOI HANDBOOK 90  Attribute Description Mandatory

                                    A location with no weight attribute
                                    is assumed to have weight one.
                                    A higher weight is selected first.
                                    If several locations have the same
                                    weight then a random choice is
                                    performed.
                                    If the weighted selection method
                                    is applied to locations that
                                    all have non-positive weights,
                                    then this method selects one
                                    of the remaining locations
                                    randomly     while   disregarding
                                    location weights.
                                    Note: The weighting allows for a
                                    very basic load balancing, but is
                                    also a way to ensure that some
                                    locations can only be addressed
                                    directly (for example, by country or
                                    locatt/attributes).

href The URL for the location. Yes

weight The weight (a floating point No between zero and one) that should
apply to this location when performing a weighted selection.

country Country of the requester. Possible No values: two-letter country
codes according to ISO 3166-1.

11.4.2 10320/LOC: EXAMPLE The table below shows the DOI record returned
for doi:10.123/456. Table 10 DOI record with redirection graph Index
Type Data

1 URL https://www.defaultexample.com

DOI HANDBOOK 91  Index Type Data

1000 10320/LOC `<locations>`{=html} `<location    id="0"
                                                                              href="https://uk.example.com/"
                                                                              country="gb"      weight="0"     />`{=html}
`<location id="1" href="https://
                                                                              www1.example.com/" weight="1" /
                                                                              >`{=html}
`<location id="2" href="https://
                                                                              www2.example.com/" weight="1" /
                                                                              >`{=html}
`</locations>`{=html}

With this example, the DOI resolver will apply the default selection
method order - it means: 1) locatt; 2) country; 3) weighted - as
illustrated below. If the DOI resolver does not understand the 10320/LOC
element type (or is requested to ignore it), then it will select the URL
element type: https://www.defaultexample.com. Table 11 Resolution
request examples with result Resolution request Selection method Result

                                        1. The locatt method does not

10.123/456 from a requester https://uk.example.com/ apply. located in
the UK 2. The resolver applies the country method. It selects
https://uk.example.com/ and stops (single matching selection).

                                        1. The locatt method does not

10.123/456 from a requester https://www1.example.com/ or apply. located
outside of the UK https://www2.example.com/ 2. The resolver applies the
country method: no URL can be selected. 3. The resolver applies the
weighted method to https:// www1.example.com/ and
https://www2.example.com/. They have the same weight, it selects one of
these two URLs randomly.

                                        1. The resolver applies the locatt

10.123/456?locatt=id:1 https://www1.example.com/ meth-od with id="1". It
selects https://www1.example.com/ and stops (single matching selection).

                                        1. The resolver applies the locatt

10.123/456?locatt=id:0 https://uk.example.com/ meth-od with id="0". It
selects https://uk.example.com/ and stops (single matching selection).

DOI HANDBOOK 92  Resolution request Selection method Result

                                      1. The resolver applies

10.123/456?locatt=country:gb https://uk.example.com/ the locatt meth-od
with country="gb". It selects https:// uk.example.com/ and stops (single
matching selection).

                                      1. The resolver applies the locatt

10.123/456?locatt=country:us https://www1.example.com/ or meth-od with
country="us": no with requester located in US https://www2.example.com/
URL can be selected. 2. The resolver applies the country method with the
country of the re-quester: no URL can be selected. 3. The resolver
applies the weighted method to https:// www1.example.com/ and
https://www2.example.com/. They have the same weight, it selects one of
these two URLs randomly.

11.4.3 10320/LOC AT PREFIX LEVEL Any location information (information
specified through a 10320/LOC element) that applies to all or most DOI
names under a prefix can be stored at prefix level: this information
applies to all DOI names under that prefix. If specific location
in-formation is stored at DOI name level then this information overrides
information stored at prefix level. Location information is stored at
prefix level by using the HS_NAMESPACE element in the record of the
prefix Handle (0.NA/`<prefix>`{=html}): the HS_NAMESPACE element points
to another Handle or DOI name which will store a 10320/LOC element.
Typically, this element will contain URL templates. For more information
about the HS_NAMESPACE element, see the Handle.net Technical Manual. The
following figure shows the example of the prefix Handle 0.NA/10.5237
where the 10320/LOC element is stored in the prefix record.

DOI HANDBOOK 93 Figure 23 10320/LOC at prefix level

11.5 PREFIX HANDLE EXAMPLE The figure below shows the record of the
prefix Handle 0.NA/10.1009.

Figure 24 Prefix Handle Record example The table below describes the
elements of the 0.NA/10.1009 record. Table 12 0.NA/10.1009 elements Type
Index Description

1 HS_ADMIN 100 RA or registrant's prefix administrator: can create

DOI HANDBOOK 94  Type Index Description

                                                                                      Handles (DOI names)
                                                                                      under prefix 10.1009.
                                                                                      This administrator is
                                                                                      identified1)        by
                                                                                      200:0.NA/10.1009 which
                                                                                      points to the index
                                                                                      200 in this identifier
                                                                                      (HS_VLIST).

2 HS_ADMIN 101 Prefix administrator of the DOI technical support service
pro- vider: can create and delete Handles (DOI names) under prefix
10.1009; can create and delete prefixes deriving from 10.1009.

3 HS_SERV 1 Points to the 10.SERV/ CROSSREF Handle which locates the
Local Handle Service (LHS) sites managing the DOI names under prefix
10.1009.

4 HS_VLIST 300 List of administrators (list of public keys).

5 EMAIL 3 Email address.

6 HS_SIGNATURE 400 Signature over the prefix Handle.

1)  An administrator is identified in the Handle System by a public key
    stored in a Handle Record (in this example, the public key is at
    index 200 of 0.NA/10.1009 record). User authentication is performed
    by a Handle System service through a PKI challenge-response.

11.6 SYSTEM TOOLS The DOI technical support service provider provides
servlets and tools that some users and programmers may find useful. The
table below lists some of them. Contact the DOI technical support
service provider at doi- admin@doi.org for information. DOI HANDBOOK 95
Table 13 Handle tools Name Description

net.handle.batch.DOIBatch A batch loader for DOI names.

net.handle.apps.admin_servlets The servlets used for administering
Handles via the web, useful if you want to allow DOI name administration
from a local web server.

net.handle.apps.simple If you do decide to roll your own Handle
software, this package has a number of examples of how to use the Handle
client library.

net.handle.apps.tools, net.handle.apps.site_tool A number of utilities
for low-level maintenance of a Handle server. Make sure to check there
before writing anything along these lines yourself.

DOI HANDBOOK 96 Chapter 11

GLOSSARY

This section contains terms which are relevant to the document content.
The terms marked \* are as specified in ISO 26324.

In This Chapter

DOI HANDBOOK 97 12.1 A actionable Capable of resolution by a system on
the Internet. For example, in an Internet Web browser, an actionable
identifier can be "clicked on" and some action takes place.

allowed value\* An item which may be used as a value of an element.

API Application Programming Interface. A way for two or more computer
programs to communicate with each other. It is a type of software
interface, offering a service to other pieces of software. A document or
standard that describes how to build or use such a connection or
interface is called an API specification. A computer system that meets
this standard is said to implement or expose an API. The term API may
refer either to the specification or to the implementation.

12.2 D DO Digital Object. A sequence of bits, or a set of sequences of
bits, that is used to represent a digital, physical or virtual entity in
the Digital Object Architecture (DOA).

DOI Directory A virtual service consisting of Handle System services and
web proxies located and con-figured to provide highly reliable
resolution, administration, and backup for all DOI names.

DOI System Metadata Metadata associated with a referent within the DOI
System, based on a structured data model that supports unambiguous
description.

DOI name\* A string that identifies a unique object within the DOI
System.

DOI Proxy A web server that understands the Handle System protocol
(DO-IRP), thereby acting as a gateway between the DOI System and HTTPS,
enabling resolution of a DOI name in the URL https:// syntax. Any
standard browser encountering a DOI name represented in this form will
be able to resolve it without the need to extend the web browsers
capability.

DOI record The set of elements to which a DOI name can be resolved.

DOI syntax\* Rules for the form and sequence of characters comprising
any DOI name, specifically the form and character of a prefix element,
separator and suffix element.

DOI HANDBOOK 98 DOI System\* Social and technical infrastructure for the
assignment and administration of DOI names as identifiers in
computer-readable form through assignment, resolution, referent
description, administration, etc.

12.3 G GHR® Global Handle Registry. A component of the Handle System
which provides first-level resolution of Handles. Stores the information
necessary to locate the LHS responsible for any Handle in the system.

12.4 H Handle Actionable identifier concept underlying the Handle
System.

Handle System® The technology used as the resolution component of the
DOI system. The Handle System is a general- purpose distributed
information system designed to provide an efficient, exten-sible, and
secured global name service for use on networks such as the Internet.
The Handle System is a particular implementation of the DO-IRP (Digital
Object - Identifier / Resolution Protocol) which is part of the Digital
Object Architecture (DOA).

HTTP Hypertext Transfer Protocol. An application layer protocol in the
Internet protocol suite model for distributed, collaborative, hypermedia
information systems. HTTP is the founda-tion of data communication for
the World Wide Web, where hypertext documents include hyperlinks to
other resources that the user can easily access, for example by a mouse
click or by tapping the screen in a web browser.

HTTPS Hypertext Transfer Protocol Secure. An extension of HTTP. It is
used for secure communica-tion over a computer network, and is widely
used on the Internet. In HTTPS, the communi-cation protocol is encrypted
using Transport Layer Security (TLS) or, formerly, Secure Sock-ets Layer
(SSL).

12.5 I interoperability\* Ability of independent systems to exchange
meaningful information and initiate actions from each other, in order to
operate together to mutual benefit.

International Organization for Standardization (ISO) Standards setting
organization with National Standards Bodies as members which publishes
international standards and other documents.

ISO 26324 ISO 26324 Information and documentation --- Digital object
identifier system. The interna-tional standard published by ISO which
specifies the DOI System. The 2025 document is the third edition and
revises the original document published in 2012.

DOI HANDBOOK 99 12.6 L LHS Local Handle Service. A component of the
Handle System which provides resolution and administration services for
Handles belonging to a given namespace.

Linked Data Structured data which is interlinked with other data so it
becomes more useful through semantic queries. It builds upon standard
Web technologies such as HTTP, RDF and URIs, but rather than using them
to serve web pages only for human readers, it extends them to share
information in a way that can be read automatically by computers.

12.7 M metadata\* Specific data associated with a referent within the
DOI System based on a structured da-ta model that enables the referent
of the DOI name to be associated with data of any desired degree of
precision and granularity to support identification, description and
services.

multiple resolution Resolution of a DOI name returning multiple
resources.

12.8 O opaque string\* Syntax string that has no meaning discernible by
simple inspection. (To discover meaning, metadata is required.)

12.9 P persistence\* Existing, and able to be used in services outside
the direct control of the issuing assigner, without a stated time limit.

12.10 R RA Registration Agency. An RA provides DOI-based services to one
or several communities of users. An RA can be considered as a module of
the DOI System, serving a constituency.

referent\* Entity identified by a DOI name.

DOI HANDBOOK 100 registrant The registrant of a DOI name provides and
maintains the metadata assigned to the DOI name. They may also assign
the DOI name suffix.

registration authority Entity appointed by ISO to manage the allocation
of names to codes under the auspices of an international standard. A
registration authority agreement between ISO and the registration
authority sets out the obligations and responsibilities of each.

resolution\* Process of submitting a DOI name to a network service and
receiving in return one or more pieces of current information related to
the identified object such as a location (URL) of the object or an email
address, etc.

REST REpresentational State Transfer. An architectural style that
defines a set of constraints to be used for creating web services. REST
API is a way of accessing web services in a simple and flexible way.

12.11 S single resolution Resolution of a DOI name returning a single
URL.

12.12 U URL Uniform Resource Locator. Colloquially termed a web address,
is a reference to a web resource that specifies its location on a
computer network and a mechanism for retrieving it. URLs occur most
commonly to reference web pages but are also used for file transfer,
email, database access, and many other applications.

DOI HANDBOOK 101 INDEX

A

Allowed Value Sets
......................................................................................................................................
83

B

Broken Link
...................................................................................................................................................
21 Board of Directors
........................................................................................................................................
29 Board Meetings
............................................................................................................................................
29

C

Check Digits
.................................................................................................................................................
39 Content Negotiation
......................................................................................................................................
60 Choose-by Mechanism
.................................................................................................................................
65

D

Digital Object Architecture
............................................................................................................................
22 Data Model Extension
..................................................................................................................................
49

F

fees
...............................................................................................................................................................
27

G

DOI HANDBOOK 102 Global Handle Registry
................................................................................................................................
53 GHR
..............................................................................................................................................................
53

M

Metadata
.........................................................................................................................................................
9 metadata model
............................................................................................................................................
47 metadata model policy
.................................................................................................................................
47

O

Other Identifier Services
..........................................................................................................................
OpenURL
......................................................................................................................................................
59

P

prefix
.............................................................................................................................................................
11 policies
..........................................................................................................................................................
33 parameter passing
........................................................................................................................................
63 policies
.....................................................................................................................................................

Q

QR code
.......................................................................................................................................................
15

R

Resolution Services
......................................................................................................................................
13 Redirection
....................................................................................................................................................
13 Registration Agencies
...................................................................................................................................
14

S

suffix
..............................................................................................................................................................
11

W

Which RA?
....................................................................................................................................................
63

DOI HANDBOOK 103 
