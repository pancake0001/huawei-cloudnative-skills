# Verification Method

1. Run the command without `confirm=true`; verify that it returns an R2 preview and creates no CR.
2. Run with a known cluster, exact node name, and `confirm=true`.
3. Verify that the returned CR name is unique, contains the node provider ID label, and reaches a terminal phase.
4. Verify that component health and at least one returned configuration section are present when collection succeeds.
5. Test an invalid cluster ID and invalid node name; confirm that the tool stops without creating a CR.
