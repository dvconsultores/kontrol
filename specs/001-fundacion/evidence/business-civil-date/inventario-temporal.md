# Inventario temporal del backend · medido en `4c94906` (2026-10-28)

Generado con un análisis AST de `resources/backend/app` (anotaciones `Mapped[...]` y `mapped_column`).
Regla de clasificación (ADR-020): `DateTime(timezone=True)` → **INSTANT** (UTC, con zona); `Date` → **BUSINESS_DATE** (Caracas). No hay columnas `DateTime` sin zona.

**Totales:** 173 columnas ORM (123 INSTANT, 50 BUSINESS_DATE) · 82 campos Pydantic/dataclass temporales · UNCLASSIFIED_TEMPORAL_FIELDS = 0.

## Columnas ORM

| FIELD_ID | Módulo | Tabla.columna | Tipo DB | Anotación | Defecto | Clase | Nota |
|---|---|---|---|---|---|---|---|
| TF-approval_decisions.decided_at | approvals | approval_decisions.decided_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-approval_delegations.revoked_at | approvals | approval_delegations.revoked_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-approval_delegations.valid_from | approvals | approval_delegations.valid_from | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-approval_delegations.valid_to | approvals | approval_delegations.valid_to | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-approval_events.occurred_at | approvals | approval_events.occurred_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-approval_policies.valid_from | approvals | approval_policies.valid_from | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-approval_policies.valid_to | approvals | approval_policies.valid_to | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-approval_requests.requested_at | approvals | approval_requests.requested_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-approval_requests.resolved_at | approvals | approval_requests.resolved_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-approval_steps.closed_at | approvals | approval_steps.closed_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-approval_steps.due_at | approvals | approval_steps.due_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-approval_steps.opened_at | approvals | approval_steps.opened_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-audit_events.event_time | audit | audit_events.event_time | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-price_list_versions.valid_from | commercial | price_list_versions.valid_from | Date | `Mapped[date]` | — | BUSINESS_DATE |  |
| TF-price_list_versions.valid_to | commercial | price_list_versions.valid_to | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-documents.effective_from | documents | documents.effective_from | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-documents.expiration_date | documents | documents.expiration_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-documents.issued_at | documents | documents.issued_at | Date | `Mapped[date|None]` | — | BUSINESS_DATE | fecha de emisión documental (Spec 046/regulatorio) |
| TF-file_security_scans.scanned_at | documents | file_security_scans.scanned_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-stored_files.expires_at | documents | stored_files.expires_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT (DURATION de seguridad) |  |
| TF-stored_files.uploaded_at | documents | stored_files.uploaded_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-control_number_batches.received_at | fiscal | control_number_batches.received_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-control_numbers.used_at | fiscal | control_numbers.used_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-fiscal_documents.emitted_at | fiscal | fiscal_documents.emitted_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-fiscal_periods.end | fiscal | fiscal_periods.end | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-fiscal_periods.start | fiscal | fiscal_periods.start | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-legal_sources.effective_from | fiscal | legal_sources.effective_from | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-legal_sources.effective_to | fiscal | legal_sources.effective_to | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-legal_sources.publication_date | fiscal | legal_sources.publication_date | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-print_events.printed_at | fiscal | print_events.printed_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-tax_profiles.validity_from | fiscal | tax_profiles.validity_from | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-tax_profiles.validity_to | fiscal | tax_profiles.validity_to | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-tax_rule_versions.effective_from | fiscal | tax_rule_versions.effective_from | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-tax_rule_versions.effective_to | fiscal | tax_rule_versions.effective_to | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-homologation_records.evaluated_at | homologation | homologation_records.evaluated_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-release_versions.released_at | homologation | release_versions.released_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-mfa_challenges.consumed_at | identity_access | mfa_challenges.consumed_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-mfa_challenges.expires_at | identity_access | mfa_challenges.expires_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT (DURATION de seguridad) |  |
| TF-mfa_factors.activated_at | identity_access | mfa_factors.activated_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-mfa_factors.pending_expires_at | identity_access | mfa_factors.pending_expires_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT (DURATION de seguridad) |  |
| TF-mfa_factors.revoked_at | identity_access | mfa_factors.revoked_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-mfa_recovery_codes.used_at | identity_access | mfa_recovery_codes.used_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-password_resets.expires_at | identity_access | password_resets.expires_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT (DURATION de seguridad) |  |
| TF-password_resets.invalidated_at | identity_access | password_resets.invalidated_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-password_resets.used_at | identity_access | password_resets.used_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sessions.expires_at | identity_access | sessions.expires_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT (DURATION de seguridad) |  |
| TF-sessions.mfa_verified_at | identity_access | sessions.mfa_verified_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT (DURATION de seguridad) |  |
| TF-sessions.reauth_at | identity_access | sessions.reauth_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT (DURATION de seguridad) |  |
| TF-sessions.revoked_at | identity_access | sessions.revoked_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-user_roles.valid_from | identity_access | user_roles.valid_from | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-user_roles.valid_to | identity_access | user_roles.valid_to | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-users.last_login | identity_access | users.last_login | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-users.lockout_until | identity_access | users.lockout_until | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT (DURATION de seguridad) |  |
| TF-costing_profiles.effective_from | inventory | costing_profiles.effective_from | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-costing_profiles.effective_to | inventory | costing_profiles.effective_to | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-inventory_balances.last_rebuilt_at | inventory | inventory_balances.last_rebuilt_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-inventory_lots.expiry_date | inventory | inventory_lots.expiry_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-inventory_lots.manufacture_date | inventory | inventory_lots.manufacture_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-inventory_movements.occurred_at | inventory | inventory_movements.occurred_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-product_serials.warranty_until | inventory | product_serials.warranty_until | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-reservations.expires_at | inventory | reservations.expires_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT (DURATION de seguridad) |  |
| TF-reservations.released_at | inventory | reservations.released_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-license_artifacts.imported_at | licensing | license_artifacts.imported_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-license_artifacts.replaced_at | licensing | license_artifacts.replaced_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-license_entitlement_snapshots.taken_at | licensing | license_entitlement_snapshots.taken_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-license_states.critical_warning_start | licensing | license_states.critical_warning_start | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-license_states.last_reliable_date | licensing | license_states.last_reliable_date | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-license_states.period_end | licensing | license_states.period_end | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-license_states.period_start | licensing | license_states.period_start | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-license_states.read_only_start | licensing | license_states.read_only_start | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-license_states.verified_at | licensing | license_states.verified_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-license_sync_runs.ran_at | licensing | license_sync_runs.ran_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-drivers.expiry | master_data | drivers.expiry | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-product_presentation_versions.valid_from | master_data | product_presentation_versions.valid_from | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-product_presentation_versions.valid_to | master_data | product_presentation_versions.valid_to | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-profile_versions.effective_from | master_data | profile_versions.effective_from | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-profile_versions.effective_to | master_data | profile_versions.effective_to | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-alerts.resolved_at | notifications | alerts.resolved_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-notification_deliveries.next_attempt_at | notifications | notification_deliveries.next_attempt_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-notification_deliveries.sent_at | notifications | notification_deliveries.sent_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-notification_recipients.archived_at | notifications | notification_recipients.archived_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-notification_recipients.read_at | notifications | notification_recipients.read_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-task_events.occurred_at | notifications | task_events.occurred_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-tasks.closed_at | notifications | tasks.closed_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-tasks.due_at | notifications | tasks.due_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-ap_applications.date | purchasing | ap_applications.date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-ap_open_items.due_date | purchasing | ap_open_items.due_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-ap_payment_instruments.value_date | purchasing | ap_payment_instruments.value_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-ap_payment_schedules.due_date | purchasing | ap_payment_schedules.due_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-ap_payments.date | purchasing | ap_payments.date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-goods_receipt_lines.counted_at | purchasing | goods_receipt_lines.counted_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-goods_receipt_lines.expiry_date | purchasing | goods_receipt_lines.expiry_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-goods_receipts.arrival_at | purchasing | goods_receipts.arrival_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-goods_receipts.confirmed_at | purchasing | goods_receipts.confirmed_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-goods_receipts.inspected_at | purchasing | goods_receipts.inspected_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-goods_receipts.record_issued_at | purchasing | goods_receipts.record_issued_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-goods_receipts.unloading_scheduled_at | purchasing | goods_receipts.unloading_scheduled_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-purchase_orders.expected_date | purchasing | purchase_orders.expected_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-purchase_requisitions.need_date | purchasing | purchase_requisitions.need_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-receipt_incidents.escalated_at | purchasing | receipt_incidents.escalated_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-receipt_incidents.resolved_at | purchasing | receipt_incidents.resolved_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-supplier_invoices.issue_date | purchasing | supplier_invoices.issue_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-supplier_quotes.validity_until | purchasing | supplier_quotes.validity_until | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-official_documents.expires_at | regulatory | official_documents.expires_at | Date | `Mapped[date|None]` | — | BUSINESS_DATE | vencimiento regulatorio como fecha |
| TF-official_documents.issued_at | regulatory | official_documents.issued_at | Date | `Mapped[date|None]` | — | BUSINESS_DATE | fecha de emisión documental (Spec 046/regulatorio) |
| TF-official_registrations.expires_at | regulatory | official_registrations.expires_at | Date | `Mapped[date|None]` | — | BUSINESS_DATE | vencimiento regulatorio como fecha |
| TF-official_registrations.issued_at | regulatory | official_registrations.issued_at | Date | `Mapped[date|None]` | — | BUSINESS_DATE | fecha de emisión documental (Spec 046/regulatorio) |
| TF-permit_instances.expires_at | regulatory | permit_instances.expires_at | Date | `Mapped[date|None]` | — | BUSINESS_DATE | vencimiento regulatorio como fecha |
| TF-permit_instances.issued_at | regulatory | permit_instances.issued_at | Date | `Mapped[date|None]` | — | BUSINESS_DATE | fecha de emisión documental (Spec 046/regulatorio) |
| TF-regulatory_approval_requests.deadline | regulatory | regulatory_approval_requests.deadline | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-regulatory_contingencies.ended_at | regulatory | regulatory_contingencies.ended_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-regulatory_contingencies.started_at | regulatory | regulatory_contingencies.started_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-report_exports.exported_at | reporting | report_exports.exported_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-report_jobs.finished_at | reporting | report_jobs.finished_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-report_jobs.started_at | reporting | report_jobs.started_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-order_confirmations.checked_at | sales | order_confirmations.checked_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-pick_list_lines.picked_at | sales | pick_list_lines.picked_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-pick_lists.cancelled_at | sales | pick_lists.cancelled_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-pick_lists.confirmed_at | sales | pick_lists.confirmed_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-pick_lists.consolidated_at | sales | pick_lists.consolidated_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-pick_lists.invalidated_at | sales | pick_lists.invalidated_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sales_credit_notes.issued_at | sales | sales_credit_notes.issued_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sales_debit_notes.issued_at | sales | sales_debit_notes.issued_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sales_invoices.issued_at | sales | sales_invoices.issued_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sales_orders.billing_requested_at | sales | sales_orders.billing_requested_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sales_orders.invoiced_at | sales | sales_orders.invoiced_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sales_orders.released_at | sales | sales_orders.released_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sales_orders.submitted_at | sales | sales_orders.submitted_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sales_quotes.validity_until | sales | sales_quotes.validity_until | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-sales_returns.approved_at | sales | sales_returns.approved_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sales_returns.inspected_at | sales | sales_returns.inspected_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sales_returns.received_at | sales | sales_returns.received_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sales_returns.reentered_at | sales | sales_returns.reentered_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-sales_returns.requested_at | sales | sales_returns.requested_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-shipments.dispatched_at | sales | shipments.dispatched_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-shipments.validated_at | sales | shipments.validated_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-scheduler_handler_runs.finished_at | scheduler | scheduler_handler_runs.finished_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-scheduler_handler_runs.started_at | scheduler | scheduler_handler_runs.started_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-scheduler_runs.finished_at | scheduler | scheduler_runs.finished_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-scheduler_runs.scheduled_for | scheduler | scheduler_runs.scheduled_for | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-scheduler_runs.started_at | scheduler | scheduler_runs.started_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-idempotency_records.expires_at | system | idempotency_records.expires_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT (DURATION de seguridad) |  |
| TF-outbox_events.occurred_at | system | outbox_events.occurred_at | DateTime(tz) | `Mapped[datetime]` | — | INSTANT |  |
| TF-outbox_events.published_at | system | outbox_events.published_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-bank_transactions.txn_date | treasury | bank_transactions.txn_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-bank_transactions.value_date | treasury | bank_transactions.value_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-cash_sessions.closed_at | treasury | cash_sessions.closed_at | Date | `Mapped[date|None]` | — | BUSINESS_DATE | ídem |
| TF-cash_sessions.opened_at | treasury | cash_sessions.opened_at | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-exchange_rate_policies.effective_from | treasury | exchange_rate_policies.effective_from | Date | `Mapped[date]` | — | BUSINESS_DATE |  |
| TF-exchange_rate_policies.effective_to | treasury | exchange_rate_policies.effective_to | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-exchange_rate_sources.effective_from | treasury | exchange_rate_sources.effective_from | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-exchange_rate_sources.effective_to | treasury | exchange_rate_sources.effective_to | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-exchange_rate_sources.last_success_at | treasury | exchange_rate_sources.last_success_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-exchange_rate_sources.last_sync_at | treasury | exchange_rate_sources.last_sync_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-exchange_rates.effective_at | treasury | exchange_rates.effective_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-exchange_rates.observed_at | treasury | exchange_rates.observed_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-exchange_rates.published_at | treasury | exchange_rates.published_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-exchange_rates.rate_date | treasury | exchange_rates.rate_date | Date | `Mapped[date]` | — | BUSINESS_DATE |  |
| TF-fiscal_rules.effective_from | treasury | fiscal_rules.effective_from | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-fiscal_rules.effective_to | treasury | fiscal_rules.effective_to | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-igft_events.evaluated_at | treasury | igft_events.evaluated_at | Date | `Mapped[date|None]` | — | BUSINESS_DATE | ídem |
| TF-reconciliations.approved_at | treasury | reconciliations.approved_at | Date | `Mapped[date|None]` | — | BUSINESS_DATE | nombre *_at sobre Date (olor de nombre; sin cambio, OD-TIME-09) |
| TF-reconciliations.statement_date | treasury | reconciliations.statement_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-treasury_fx_policies.approved_at | treasury | treasury_fx_policies.approved_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-treasury_fx_policies.effective_from | treasury | treasury_fx_policies.effective_from | Date | `Mapped[date]` | — | BUSINESS_DATE |  |
| TF-treasury_fx_policies.effective_to | treasury | treasury_fx_policies.effective_to | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-treasury_rate_snapshots.rate_date | treasury | treasury_rate_snapshots.rate_date | Date | `Mapped[date]` | — | BUSINESS_DATE |  |
| TF-treasury_refunds.approved_at | treasury | treasury_refunds.approved_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-treasury_refunds.requested_at | treasury | treasury_refunds.requested_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-treasury_refunds.settled_at | treasury | treasury_refunds.settled_at | DateTime(tz) | `Mapped[datetime|None]` | — | INSTANT |  |
| TF-treasury_transfers.value_date | treasury | treasury_transfers.value_date | Date | `Mapped[date|None]` | — | BUSINESS_DATE |  |
| TF-TimestampMixin.created_at | shared | TimestampMixin.created_at | DateTime(tz) | `Mapped[datetime]` | server_default=func.now() | INSTANT |  |
| TF-TimestampMixin.updated_at | shared | TimestampMixin.updated_at | DateTime(tz) | `Mapped[datetime]` | server_default=func.now() | INSTANT |  |

## Campos de esquema (Pydantic / dataclass)

| Fichero | Clase.campo | Anotación | Clase | OpenAPI |
|---|---|---|---|---|
| app/core/license_contract.py | LicenseData.critical_warning_start | `datetime` | BUSINESS_DATE | date |
| app/core/license_contract.py | LicenseData.period_end | `datetime` | BUSINESS_DATE | date |
| app/core/license_contract.py | LicenseData.period_start | `datetime` | BUSINESS_DATE | date |
| app/core/license_contract.py | LicenseData.read_only_start | `datetime` | BUSINESS_DATE | date |
| app/modules/approvals/api.py | DelegationCreate.valid_from | `datetime|None` | BUSINESS_DATE | date |
| app/modules/approvals/api.py | DelegationCreate.valid_to | `datetime|None` | BUSINESS_DATE | date |
| app/modules/commercial/api.py | ResolverIn.as_of | `date|None` | BUSINESS_DATE | date |
| app/modules/commercial/api.py | VersionIn.valid_from | `date` | BUSINESS_DATE | date |
| app/modules/commercial/api.py | VersionIn.valid_to | `date|None` | BUSINESS_DATE | date |
| app/modules/documents/api.py | DocumentIn.effective_from | `date|None` | BUSINESS_DATE | date |
| app/modules/documents/api.py | DocumentIn.expiration_date | `date|None` | BUSINESS_DATE | date |
| app/modules/documents/api.py | DocumentIn.issued_at | `date|None` | BUSINESS_DATE | date |
| app/modules/documents/api.py | DocumentPatch.effective_from | `date|None` | BUSINESS_DATE | date |
| app/modules/documents/api.py | DocumentPatch.expiration_date | `date|None` | BUSINESS_DATE | date |
| app/modules/documents/api.py | DocumentPatch.issued_at | `date|None` | BUSINESS_DATE | date |
| app/modules/fiscal/api.py | ControlBatchCreate.received_at | `date|None` | BUSINESS_DATE | date |
| app/modules/fiscal/api.py | LegalSourceCreate.effective_from | `date|None` | BUSINESS_DATE | date |
| app/modules/fiscal/api.py | LegalSourceCreate.effective_to | `date|None` | BUSINESS_DATE | date |
| app/modules/fiscal/api.py | LegalSourceCreate.publication_date | `date|None` | BUSINESS_DATE | date |
| app/modules/fiscal/api.py | PeriodCreate.end | `date|None` | BUSINESS_DATE | date |
| app/modules/fiscal/api.py | PeriodCreate.start | `date|None` | BUSINESS_DATE | date |
| app/modules/fiscal/api.py | TaxCalculateBody.on_date | `date|None` | BUSINESS_DATE | date |
| app/modules/fiscal/api.py | TaxProfileCreate.validity_from | `date|None` | BUSINESS_DATE | date |
| app/modules/fiscal/api.py | TaxProfileCreate.validity_to | `date|None` | BUSINESS_DATE | date |
| app/modules/fiscal/api.py | TaxRuleCreate.effective_from | `date|None` | BUSINESS_DATE | date |
| app/modules/fiscal/api.py | TaxRuleCreate.effective_to | `date|None` | BUSINESS_DATE | date |
| app/modules/inventory/api.py | CostingProfileCreate.effective_from | `date|None` | BUSINESS_DATE | date |
| app/modules/inventory/api.py | CostingProfileCreate.effective_to | `date|None` | BUSINESS_DATE | date |
| app/modules/inventory/api.py | LotCreate.expiry_date | `date|None` | BUSINESS_DATE | date |
| app/modules/inventory/api.py | LotCreate.manufacture_date | `date|None` | BUSINESS_DATE | date |
| app/modules/inventory/api.py | OperationReceive.expiry_date | `date|None` | BUSINESS_DATE | date |
| app/modules/master_data/api.py | ProfileCreate.effective_from | `datetime|None` | BUSINESS_DATE | date |
| app/modules/master_data/api.py | ProfileCreate.effective_to | `datetime|None` | BUSINESS_DATE | date |
| app/modules/master_data/uom_api.py | PresentationIn.valid_from | `datetime|None` | BUSINESS_DATE | date |
| app/modules/master_data/uom_api.py | PreviewIn.date | `datetime|None` | BUSINESS_DATE | date |
| app/modules/master_data/uom_api.py | VersionIn.valid_from | `datetime|None` | BUSINESS_DATE | date |
| app/modules/notifications/api.py | AlertaOut.created_at | `datetime` | BUSINESS_DATE | date |
| app/modules/notifications/api.py | AlertaOut.resolved_at | `datetime|None` | BUSINESS_DATE | date |
| app/modules/notifications/api.py | EventoTareaOut.occurred_at | `datetime` | BUSINESS_DATE | date |
| app/modules/notifications/api.py | NotificacionOut.archived_at | `datetime|None` | BUSINESS_DATE | date |
| app/modules/notifications/api.py | NotificacionOut.created_at | `datetime` | BUSINESS_DATE | date |
| app/modules/notifications/api.py | NotificacionOut.read_at | `datetime|None` | BUSINESS_DATE | date |
| app/modules/notifications/api.py | ReglaOut.created_at | `datetime` | BUSINESS_DATE | date |
| app/modules/notifications/api.py | TareaOut.closed_at | `datetime|None` | BUSINESS_DATE | date |
| app/modules/notifications/api.py | TareaOut.created_at | `datetime` | BUSINESS_DATE | date |
| app/modules/notifications/api.py | TareaOut.due_at | `datetime|None` | BUSINESS_DATE | date |
| app/modules/notifications/delivery.py | ProveedorExterno.espera_entre_intentos | `timedelta` | DURATION | — |
| app/modules/notifications/service.py | Efecto.due_at | `datetime|None` | BUSINESS_DATE | date |
| app/modules/purchasing/api.py | ArrivalBody.arrival_at | `datetime|None` | BUSINESS_DATE | date |
| app/modules/purchasing/api.py | InvoiceCreate.issue_date | `date|None` | BUSINESS_DATE | date |
| app/modules/purchasing/api.py | OrderCreate.expected_date | `date|None` | BUSINESS_DATE | date |
| app/modules/purchasing/api.py | QuoteCreate.validity_until | `date|None` | BUSINESS_DATE | date |
| app/modules/purchasing/api.py | ReceiptCreate.unloading_scheduled_at | `datetime|None` | BUSINESS_DATE | date |
| app/modules/purchasing/api.py | ReceiptLineCreate.expiry_date | `date|None` | BUSINESS_DATE | date |
| app/modules/purchasing/api.py | RequisitionCreate.need_date | `date|None` | BUSINESS_DATE | date |
| app/modules/purchasing/api.py | ScheduleCreate.due_date | `date|None` | BUSINESS_DATE | date |
| app/modules/regulatory/api.py | ApprovalCreate.deadline | `date|None` | BUSINESS_DATE | date |
| app/modules/regulatory/api.py | OfficialDocumentCreate.expires_at | `date|None` | BUSINESS_DATE | date |
| app/modules/regulatory/api.py | OfficialDocumentCreate.issued_at | `date|None` | BUSINESS_DATE | date |
| app/modules/regulatory/api.py | PermitCreate.expires_at | `date|None` | BUSINESS_DATE | date |
| app/modules/regulatory/api.py | PermitCreate.issued_at | `date|None` | BUSINESS_DATE | date |
| app/modules/regulatory/api.py | RegistrationCreate.expires_at | `date|None` | BUSINESS_DATE | date |
| app/modules/regulatory/api.py | RegistrationCreate.issued_at | `date|None` | BUSINESS_DATE | date |
| app/modules/sales/api.py | QuoteCreate.validity_until | `date|None` | BUSINESS_DATE | date |
| app/modules/scheduler/service.py | Contexto.now | `datetime` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | BankTransactionCreate.txn_date | `date|None` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | BankTransactionCreate.value_date | `date|None` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | ExchangeRateCreate.rate_date | `date` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | FiscalRuleCreate.effective_from | `date|None` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | FiscalRuleCreate.effective_to | `date|None` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | FxConversionBody.on_date | `date|None` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | FxPolicyBody.effective_from | `date` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | IgftEvaluateBody.on_date | `date|None` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | RateObservationBody.effective_at | `datetime` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | RateObservationBody.published_at | `datetime|None` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | RatePolicyBody.effective_from | `date` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | RateSourceBody.effective_from | `date|None` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | ReconciliationCreate.statement_date | `date|None` | BUSINESS_DATE | date |
| app/modules/treasury/api.py | TransferCreate.value_date | `date|None` | BUSINESS_DATE | date |
| app/modules/treasury/rates.py | RateResolution.effective_at | `datetime` | BUSINESS_DATE | date |
| app/modules/treasury/rates.py | RateResolution.observed_at | `datetime|None` | BUSINESS_DATE | date |
| app/modules/treasury/rates.py | RateResolution.published_at | `datetime|None` | BUSINESS_DATE | date |

## Campos que se emiten como texto (sin esquema)

Muchas rutas devuelven `dict` con `isoformat()`: un INSTANT se emite con desfase (`+00:00` con la sesión en UTC, AD-5) y un BUSINESS_DATE como «AAAA-MM-DD». Casos tratados en el ciclo: `customer_statement.entries[].date` pasa a BUSINESS_DATE (B5) y las respuestas de reportes ganan `period_applied` y `period_rule` (AD-6).

## Sellos técnicos (TECHNICAL_STAMP)

| Dónde | Qué | Decisión |
|---|---|---|
| `reporting/service.py` | Sello UTC + sufijo único del nombre de exportación (02E) | Se conserva (OD-TIME-06) |
| `licensing/service.py:760` | Día UTC en la clave de idempotencia de licencias | Se conserva: técnica, no es fecha de negocio |
| `qa/e2e_nombres.py` | run_id en UTC | Se conserva (OBS-TIME-01: EXPLAINED) |
