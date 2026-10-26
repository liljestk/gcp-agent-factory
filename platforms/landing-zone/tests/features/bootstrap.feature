Feature: Trust root, org IAM and the billing-account budget
  The bootstrap stack creates only the trust-root layer, converges on a second
  plan, owns org, folder and seed IAM, and keeps CI out of the trust root.
  The read-only checks run nightly as ci-plan.

  @REQ-LZ-009 @acceptance
  Scenario: The seed project is minimal and labelled
    When I read the seed project
    Then it sits in the "trust-root" folder
    And it carries the standard labels
    And it has no VPC network
    And it enables exactly the allow-listed APIs

  @REQ-LZ-009 @acceptance
  Scenario: Bootstrap converges
    When the "bootstrap" stack is planned
    Then the plan has no changes

  @REQ-LZ-010 @security
  Scenario: Creator roles are no longer domain-wide
    When I read the organization's IAM policy
    Then "Project Creator" is held only by "gcp-org-admins"
    And "Billing Account Creator" is held by nobody

  @REQ-LZ-010 @security
  Scenario: CI identities hold exactly their allow-listed roles
    When I read every role held by a CI service account at org, folder, seed and billing-account level
    Then each identity holds exactly the roles listed for it in the design
    And none holds a role on "trust-root" or the seed project apart from the viewer roles of "ci-plan"
    And none holds "Organization Administrator", "Security Admin" or a basic role

  @REQ-LZ-010 @security
  Scenario: A deny policy keeps CI out of the trust root
    When I read the deny policies of the "trust-root" folder
    Then one denies every CI service account the trust-root permissions listed in the design

  @REQ-LZ-010 @security
  Scenario: Seed admin roles belong to the org admins
    When I read the seed project's IAM policy
    Then "Owner", "Editor" and the storage, KMS, WIF and service-account admin roles are held only by "gcp-org-admins"

  @REQ-LZ-011 @acceptance
  Scenario: The billing-account budget measures gross cost
    When I read the budgets of the billing account
    Then a monthly budget of 85 EUR exists
    And it excludes all credits
    And it alerts at 25, 50, 75, 90 and 100 percent
