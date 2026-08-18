# Real Cloud Environment Verification Report (Bedrock Model Availability & Authorization Audit)

**System:** Missouri Arbiter: Multi-Agent Maritime Orchestration Engine  
**Verification Date:** August 18, 2026  
**Enforced Environment Mode:** `ARBITER_MODE=CLOUD`  
**IAM Principal:** `arn:aws:iam::599729677443:root` (Account Root User)  
**AWS Region:** `ap-south-1`  
**Primary Reasoning Model:** `amazon.nova-lite-v1:0`  
**Vector Embedding Model:** `amazon.titan-embed-text-v2:0`  

---

## 1. Bedrock Foundation Model Availability Diagnostics

Ran `GetFoundationModelAvailability` via AWS Bedrock control plane for target models:

### Model A: `amazon.nova-lite-v1:0` (Amazon Nova Lite)

```json
{
  "modelId": "amazon.nova-lite-v1",
  "authorizationStatus": "NOT_AUTHORIZED",
  "agreementAvailability": {
    "status": "AVAILABLE"
  },
  "entitlementAvailability": "AVAILABLE",
  "regionAvailability": "AVAILABLE"
}
```

- `authorizationStatus`: `NOT_AUTHORIZED`
- `agreementAvailability.status`: `AVAILABLE`
- `agreementAvailability.errorMessage`: `None`
- `entitlementAvailability`: `AVAILABLE`
- `regionAvailability`: `AVAILABLE`

### Model B: `amazon.titan-embed-text-v2:0` (Amazon Titan Embeddings V2)

```json
{
  "modelId": "amazon.titan-embed-text-v2",
  "authorizationStatus": "NOT_AUTHORIZED",
  "agreementAvailability": {
    "status": "AVAILABLE"
  },
  "entitlementAvailability": "AVAILABLE",
  "regionAvailability": "AVAILABLE"
}
```

- `authorizationStatus`: `NOT_AUTHORIZED`
- `agreementAvailability.status`: `AVAILABLE`
- `agreementAvailability.errorMessage`: `None`
- `entitlementAvailability`: `AVAILABLE`
- `regionAvailability`: `AVAILABLE`

---

## 2. Agreement Offer & IAM Diagnostics

1. **Agreement Offer Check (`ListFoundationModelAgreementOffers`):**
   - Both models returned: `ValidationException: Agreement not supported for this model`.
   - **Conclusion:** Amazon-native models do not require third-party EULA marketplace agreements.

2. **IAM Principal Verification:**
   - Authenticated Principal: `arn:aws:iam::599729677443:root` (Account Root User).
   - **Conclusion:** Root user has full administrative privileges; the runtime failure is not caused by missing IAM policies (`bedrock:InvokeModel` / `bedrock:InvokeModelWithResponseStream`).

---

## 3. Real Runtime Errors

| Target Model | Region | API Call | Error Response |
| :--- | :---: | :---: | :--- |
| `amazon.nova-lite-v1:0` | `ap-south-1` | `converse` / `invoke_model` | `ValidationException: Operation not allowed` |
| `apac.amazon.nova-lite-v1:0` | `ap-south-1` | `converse` / `invoke_model` | `ValidationException: Operation not allowed` |
| `amazon.titan-embed-text-v2:0` | `ap-south-1` | `invoke_model` | `ValidationException: Operation not allowed` |

---

## 4. Diagnosis & Recommended AWS Console / Support Action

### Diagnostic Analysis:
- `agreementAvailability`, `entitlementAvailability`, and `regionAvailability` are all **`AVAILABLE`**.
- The IAM principal is the **Account Root User**.
- The service-side state returns **`authorizationStatus = NOT_AUTHORIZED`**, causing Bedrock runtime to block invocations with `ValidationException: Operation not allowed`.

### Action Required:
1. Open **AWS Console -> Amazon Bedrock -> Model access** (Region: `ap-south-1`).
2. Click **Modify Model Access** / **Request Model Access**.
3. Select **Amazon Nova Lite** and **Amazon Titan Embeddings V2** and click **Save changes / Request access**.
4. If model access page indicates pending verification for a new/restricted AWS account, contact **AWS Support** under **Service Limit Increase / Bedrock Model Access** to unblock service-side authorization for account `599729677443`.

---

## 5. Hard Stop & Phase 5 Status

```text
[BEDROCK] MODEL = amazon.nova-lite-v1:0
[BEDROCK] REGION = ap-south-1
[BEDROCK] REAL API = FAIL

[TITAN] REAL API = FAIL
[TITAN] DIMENSION = None

[COCKROACHDB] REAL CONNECTION = FAIL
```

- **Phase 5 remains strictly BLOCKED.**
- Phase 5 will not start until both `Nova Lite REAL INVOCATION = PASS` and `Titan REAL INVOCATION = PASS`.
