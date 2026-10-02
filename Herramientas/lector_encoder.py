$f = "C:\Users\printer\Downloads\pq0_log.txt"
Remove-Item $f -ErrorAction SilentlyContinue
1..150 | ForEach-Object {
    $j = curl.exe -s http://192.168.79.134:8080/api/headManagerBoards/0/printQueues/0 | ConvertFrom-Json
    "{0:HH:mm:ss.fff} state={1} pdOffset={2} pdCount={3} pos={4} fire={5} ops={6}" -f (Get-Date), $j.state.name, $j.encoder.pdOffset, $j.encoder.diagnostics.pdCount, $j.encoder.diagnostics.position, $j.encoder.diagnostics.fireRequests, $j.printOperations.Count | Add-Content $f
    Start-Sleep -Milliseconds 200
}
notepad $f