@REQ-REPO-007
Feature: Coding agents can't run destructive commands
  Infrastructure changes reach GCP only through CI (INV-03). The Claude Code
  PreToolUse hook stops a coding agent before it runs a destructive shell command.

  Scenario Outline: Destructive commands are blocked
    When the agent runs "<command>" in the "<tool>" tool
    Then the command is blocked because of "<reason>"

    Examples:
      | tool       | command                                                | reason                        |
      | Bash       | tofu apply -auto-approve                               | not a local apply/destroy     |
      | Bash       | terraform destroy                                      | not a local apply/destroy     |
      | PowerShell | tofu destroy -target=module.agents                     | not a local apply/destroy     |
      | Bash       | gcloud projects delete gcp-agent-factory-dev-k3x9      | deleting cloud resources      |
      | Bash       | gcloud iam service-accounts keys create key.json       | service-account keys          |
      | Bash       | gcloud billing projects unlink gcp-agent-factory-dev   | billing changes               |
      | Bash       | gsutil rm -r gs://gcp-agent-factory-tfstate            | deleting bucket objects       |
      | Bash       | gcloud storage rm --recursive gs://bucket              | deleting bucket objects       |
      | Bash       | bq rm -f -d dp_finops                                  | deleting BigQuery resources   |
      | Bash       | git push --force origin main                           | force-pushing                 |
      | Bash       | git push -f origin main                                | force-pushing                 |
      | Bash       | git push origin +main                                  | force-pushing                 |
      | Bash       | rm -rf /                                               | recursive delete              |
      | Bash       | rm -rf ~                                               | recursive delete              |

  Scenario Outline: Everyday commands are allowed
    When the agent runs "<command>" in the "<tool>" tool
    Then the command is allowed

    Examples:
      | tool       | command                                     |
      | Bash       | git push -u origin main                     |
      | Bash       | tofu plan -out=tfplan                       |
      | Bash       | tofu fmt -check -recursive modules          |
      | Bash       | gcloud run services describe orchestrator   |
      | Bash       | rm -rf .terraform                           |
      | Bash       | ls -la && echo done                         |
      | PowerShell | Get-ChildItem -Recurse                      |
      | Read       | tofu apply -auto-approve                    |

  Scenario: Malformed hook input fails open
    When the guard receives the raw input "not json"
    Then the command is allowed
