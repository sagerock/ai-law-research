# Source-Linked Brief 10-Case Pilot

Run date: July 11, 2026

## Outcome

- 10 candidates generated with unused Claude subscription capacity.
- 10 passed JSON schema, content-hash, source-ID, opinion-part, and word-count validation.
- 5 passed semantic claim-to-source review and remain published.
- 5 were removed from public display and placed on semantic-review hold.
- 0 parse, stale-hash, unknown-ID, or database failures.
- The Original briefs were never modified.

## Published

| Case | ID | Stable passages |
|---|---:|---:|
| Celotex Corp. v. Catrett | 111722 | 845 |
| International Shoe Co. v. Washington | 104200 | 448 |
| Erie Railroad Co. v. Tompkins | 103012 | 1,439 |
| Brown v. Board of Education | 105221 | 278 |
| Louisville & Nashville Railroad v. Mottley | 96889 | 117 |

## Held For Revision

| Case | ID | Review finding |
|---|---:|---|
| Marbury v. Madison | 84759 | Several correct propositions cited incomplete passages about ministerial duty, mandamus, and executive control. |
| Hickman v. Taylor | 104357 | One rule overstated mental-impression protection; several links supported only part of their claims. |
| Griswold v. Connecticut | 107082 | One majority claim conflated Douglas's penumbral analysis with the Ninth Amendment concurrence. |
| Hanna v. Plumer | 107024 | One fact overstated Massachusetts service law; one rule lacked support in its assigned passages. |
| Washington v. Glucksberg | 118144 | Historical and procedural details were not fully supported by their assigned passages. |

## Lessons

Real source IDs are necessary but not sufficient: a model can cite a genuine nearby sentence that supports only part of a broader claim. Future batches are therefore saved as `pending` and hidden from the API until semantic review marks them approved. Semantic-review failures are durable and removed from the automatic queue until deliberately revised.

The dedicated pilot uses one fresh Claude session per case, optional dissents, bounded source packets for long opinions, full-opinion passage persistence, and transactional candidate saves. The legacy 300-brief Sunday workflow remains unchanged.
