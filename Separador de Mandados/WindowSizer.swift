import SwiftUI
import AppKit

/// Força o tamanho da janela e (opcional) trava o redimensionamento.
/// Funciona no macOS 12+ (independente de `.defaultSize`).
struct WindowSizer: NSViewRepresentable {
    var size: CGSize
    var lock: Bool = false

    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async {
            guard let win = view.window else { return }
            let s = NSSize(width: size.width, height: size.height)

            // define o tamanho do "conteúdo" da janela (área útil)
            win.setContentSize(s)

            if lock {
                // trava o redimensionamento
                win.minSize = s
                win.maxSize = s
                win.styleMask.remove(.resizable)
            } else {
                // ainda permite redimensionar, mas começa nesse tamanho
                win.minSize = NSSize(width: 640, height: 440)
            }
        }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {}
}
