import Foundation
import AppKit
import CoreGraphics

let targetApp = CommandLine.arguments.count >= 2 ? CommandLine.arguments[1] : "ChatGPT"

let frontApp = NSWorkspace.shared.frontmostApplication?.localizedName ?? ""
let mouseLoc = CGEvent(source: nil)?.location ?? CGPoint.zero

var result: [String: Any] = [
    "app": targetApp,
    "frontmost_app": frontApp,
    "mouse_x": round(Double(mouseLoc.x) * 10) / 10,
    "mouse_y": round(Double(mouseLoc.y) * 10) / 10,
    "running": false,
    "has_window": false
]

if let app = NSWorkspace.shared.runningApplications.first(where: {
    ($0.localizedName ?? "").caseInsensitiveCompare(targetApp) == .orderedSame
}) {
    result["running"] = true
    result["pid"] = Int(app.processIdentifier)
    result["frontmost"] = (app.localizedName == frontApp)

    if let list = CGWindowListCopyWindowInfo([.optionAll, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] {
        var best: [String: Any]? = nil
        var bestArea: Double = -1.0
        for w in list {
            guard let ownerPid = w[kCGWindowOwnerPID as String] as? Int,
                  ownerPid == Int(app.processIdentifier) else { continue }
            let layer = (w[kCGWindowLayer as String] as? Int) ?? 0
            if layer != 0 { continue }
            guard let bounds = w[kCGWindowBounds as String] as? [String: Any],
                  let bw = bounds["Width"] as? Double,
                  let bh = bounds["Height"] as? Double,
                  bw > 200, bh > 200 else { continue }
            let area = bw * bh
            if area > bestArea {
                bestArea = area
                best = w
            }
        }
        if let w = best,
           let bounds = w[kCGWindowBounds as String] as? [String: Any],
           let wid = w[kCGWindowNumber as String] as? Int {
            result["has_window"] = true
            result["window_id"] = wid
            result["title"] = (w[kCGWindowName as String] as? String) ?? ""
            result["x"] = bounds["X"] ?? 0
            result["y"] = bounds["Y"] ?? 0
            result["width"] = bounds["Width"] ?? 0
            result["height"] = bounds["Height"] ?? 0
        }
    }
}

if let data = try? JSONSerialization.data(withJSONObject: result, options: []),
   let str = String(data: data, encoding: .utf8) {
    print(str)
}
