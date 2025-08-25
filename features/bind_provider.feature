Feature: BIND DNS Provider
  As a system administrator
  I want to use the BIND DNS provider
  So that I can manage DNS records on BIND DNS servers

  Background:
    Given the BIND DNS server is running
    And I have a test zone configured

  Scenario: BIND provider initialization
    Given I have BIND provider configuration
    When I initialize the BIND provider
    Then the provider should be configured correctly
    And the TSIG key should be loaded if available

  Scenario: DNS record creation via BIND
    Given I have BIND provider configuration
    Given I have a new DNS record to create
    When I initialize the BIND provider
    When I create the DNS record using BIND provider
    Then the record should be created in BIND
    And the record should be resolvable

  Scenario: DNS record update via BIND
    Given there is an existing DNS record
    When I update the record using BIND provider
    Then the record should be updated in BIND
    And the new value should be resolvable

  Scenario: DNS record deletion via BIND
    Given there is an existing DNS record
    When I delete the record using BIND provider
    Then the record should be removed from BIND
    And the record should not be resolvable

  Scenario: Zone transfer via BIND
    Given there are DNS records in the zone
    When I perform a zone transfer
    Then I should receive all zone records
    And the records should be properly formatted

  Scenario: Invalid zone handling
    Given I specify an invalid zone name
    When I attempt DNS operations with invalid zone
    Then the operations should fail gracefully with invalid zone
    And appropriate error messages should be shown for invalid zone

  Scenario: Large zone handling
    Given I have a zone with many records
    When I retrieve all records from the zone
    Then all records should be retrieved
    And the bulk retrieval operation should complete within reasonable time
