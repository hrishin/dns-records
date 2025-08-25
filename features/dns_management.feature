Feature: DNS Records Management
  As a system administrator
  I want to manage DNS records through the DNS Records Manager
  So that I can automate DNS record creation, updates, and deletion

  Background:
    Given the DNS Records Manager is configured with BIND provider
    And the BIND DNS server is running
    And I have a test zone configured

  Scenario: Create new DNS records from CSV
    Given I have a CSV file with new DNS records
    When I process the CSV file to create DNS records
    Then the DNS records should be created successfully
    And the records should be resolvable via DNS queries

  Scenario: Update existing DNS records
    Given there are existing DNS records in the zone
    When I update the IP addresses for existing records
    Then the DNS records should be updated successfully
    And the new IP addresses should be resolvable

  Scenario: Delete DNS records
    Given there are existing DNS records in the zone
    When I remove records from the CSV file
    Then the removed records should be deleted from DNS
    And the remaining records should still be resolvable

  Scenario: Idempotent operations
    Given the DNS records are already in the desired state
    When I process the same CSV file again
    Then no changes should be made to the DNS zone
    And the operation should complete successfully

  Scenario: Dry run mode
    Given I have a CSV file with DNS record changes
    When I run the DNS manager in dry run mode
    Then no actual changes should be made to DNS
    And I should see a summary of proposed changes

  Scenario: Invalid DNS records handling
    Given I have a CSV file with valid and invalid DNS records
    When I process the CSV file
    Then invalid records should be skipped
    And valid records should be processed successfully

  Scenario: Zone transfer and record retrieval
    Given there are DNS records in the zone
    When I retrieve all records for the zone
    Then I should get a complete list of all records
    And the records should include correct FQDN and IP mappings

  Scenario: Large number of records
    Given I have a CSV file with many DNS records
    When I process the large CSV file
    Then all records should be processed successfully
    And the operation should complete within reasonable time

  Scenario: Concurrent operations
    Given multiple DNS operations are running simultaneously
    When I perform concurrent DNS updates
    Then all operations should complete successfully
    And the DNS zone should remain consistent
