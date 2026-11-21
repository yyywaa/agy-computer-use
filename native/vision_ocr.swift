import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count >= 2 else {
    fputs("Usage: vision_ocr <image_path> [window_width] [window_height]\n", stderr)
    exit(1)
}

let imgPath = CommandLine.arguments[1]
let winW = CommandLine.arguments.count >= 3 ? Double(CommandLine.arguments[2]) : nil
let winH = CommandLine.arguments.count >= 4 ? Double(CommandLine.arguments[3]) : nil

guard let nsImage = NSImage(contentsOfFile: imgPath),
      let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fputs("Failed to load image: \(imgPath)\n", stderr)
    exit(2)
}

let outW = winW ?? Double(cgImage.width)
let outH = winH ?? Double(cgImage.height)

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = false

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
do {
    try handler.perform([request])
} catch {
    fputs("Vision OCR error: \(error)\n", stderr)
    exit(3)
}

var results: [[String: Any]] = []
for obs in request.results ?? [] {
    guard let top = obs.topCandidates(1).first else { continue }
    let box = obs.boundingBox
    let x = box.origin.x * outW
    let y = (1.0 - box.origin.y - box.size.height) * outH
    let w = box.size.width * outW
    let h = box.size.height * outH
    results.append([
        "text": top.string,
        "confidence": Double(top.confidence),
        "x": round(x * 10) / 10,
        "y": round(y * 10) / 10,
        "w": round(w * 10) / 10,
        "h": round(h * 10) / 10,
        "cx": round((x + w / 2.0) * 10) / 10,
        "cy": round((y + h / 2.0) * 10) / 10
    ])
}

results.sort { a, b in
    let ay = a["y"] as! Double
    let by = b["y"] as! Double
    if abs(ay - by) > 8.0 { return ay < by }
    return (a["x"] as! Double) < (b["x"] as! Double)
}

if let data = try? JSONSerialization.data(withJSONObject: results, options: []),
   let str = String(data: data, encoding: .utf8) {
    print(str)
}
