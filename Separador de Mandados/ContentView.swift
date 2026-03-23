import SwiftUI
import UniformTypeIdentifiers
import AppKit

// ---- Estilos compatíveis (substituem .borderedProminent / .bordered) ----

struct FilledButtonStyle: ButtonStyle {
    let tint: Color
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.vertical, 10)
            .padding(.horizontal, 10)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(
                        LinearGradient(
                            gradient: Gradient(colors: [
                                Color(red: 1.0, green: 0.9, blue: 0.4),
                                Color(red: 0.85, green: 0.7, blue: 0.3)
                            ]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                        .opacity(configuration.isPressed ? 0.85 : 1.0)
                    )
            )
            .foregroundColor(.black)
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(Color(red: 0.6, green: 0.5, blue: 0.2), lineWidth: 1)
            )
    }
}

struct OutlineButtonStyleCompat: ButtonStyle {
    let tint: Color
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.vertical, 10)
            .padding(.horizontal, 10)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(
                        LinearGradient(
                            gradient: Gradient(colors: [
                                Color(red: 1.0, green: 0.9, blue: 0.4),
                                Color(red: 0.85, green: 0.7, blue: 0.3)
                            ]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                        .opacity(configuration.isPressed ? 0.9 : 1)
                    )
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(Color(red: 0.6, green: 0.5, blue: 0.2), lineWidth: 1.2)
            )
            .foregroundColor(.black)
    }
}

// ============================== VIEW ==============================

struct ContentView: View {
    @State private var isTargeted = false
    @State private var messages: [String] = []

    // lembra a última pasta "principal" (Mandados a Separar) e a última saída
    @State private var lastPrincipalDir: URL? = nil
    @State private var lastOutDir: URL? = nil

    @State private var queue: [URL] = []
    @State private var currentItem: URL? = nil
    @State private var isProcessing = false
    
    // Modo debug para arrastar header e ajustar tamanho
    @AppStorage("headerPositionX") private var savedX: Double = 275
    @AppStorage("headerPositionY") private var savedY: Double = 30
    @AppStorage("titleFontSize") private var titleFontSize: Double = 26
    @AppStorage("subtitleFontSize") private var subtitleFontSize: Double = 12
    
    @State private var headerPosition = CGPoint(x: 275, y: 30)
    @State private var debugMode = false  // Ativa/desativa modo debug
    
    // Carrega as posições salvas ao iniciar
    init() {
        _headerPosition = State(initialValue: CGPoint(x: savedX, y: savedY))
    }

    // Tamanho/spacing — todos os botões terão a MESMA largura/altura
    private let buttonWidth: CGFloat = 220
    private let columnVSpacing: CGFloat = 20  // Reduzido para botões ficarem mais próximos
    private let columnsHSpacing: CGFloat = 30
    private let bottomBarSpacing: CGFloat = 24

    var body: some View {
        ZStack {
            // Background image
            Image("fundo")
                .resizable()
                .aspectRatio(contentMode: .fill)
                .ignoresSafeArea(.all)
            
            VStack(spacing: 12) {
                header
                    .onTapGesture(count: 3) {  // Triplo clique ativa modo debug
                        debugMode.toggle()
                        if debugMode {
                            messages.append("🔧 Modo Debug ATIVADO - Arraste para mover, use +/- para ajustar tamanhos")
                            messages.append("📏 T = Tamanho do título | S = Tamanho do subtítulo")
                        } else {
                            // SALVA as configurações ao desativar o modo debug
                            savedX = headerPosition.x
                            savedY = headerPosition.y
                            messages.append("✅ Modo Debug DESATIVADO - Configurações SALVAS!")
                            messages.append("📍 Posição: x:\(Int(headerPosition.x)) y:\(Int(headerPosition.y))")
                            messages.append("📏 Tamanhos: Título:\(Int(titleFontSize))pt Subtítulo:\(Int(subtitleFontSize))pt")
                        }
                    }

                Spacer()  // Empurra tudo para baixo

                // Drop zone GRANDE centralizado
                HStack {
                    Spacer()
                    dropZone()
                        .frame(width: 300, height: 200)  // MUITO MAIOR
                    Spacer()
                }
                .padding(.bottom, 40)
                .offset(y: 75)  // Move o ícone 75 pontos (≈3cm) para baixo

                // Todos os botões na parte inferior
                twoColumnButtons
                    .padding(.bottom, 15)

                bottomBar
                    .padding(.bottom, 30)  // Um pouco acima da borda inferior

                if isProcessing {
                    HStack {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .yellow))
                            .scaleEffect(0.8)
                        Spacer()
                    }
                    .padding(.horizontal)
                    .padding(.top, 10)
                }
            }
            .padding(16)
        }
        .frame(minWidth: 1110, minHeight: 840) // janela maior

        // Ícone canto superior direito
        .overlay(alignment: .topTrailing) {
            Image("cornerIcon")
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: 56, height: 56)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .shadow(color: .black.opacity(0.25), radius: 6, x: 0, y: 3)
                .padding(.top, 8)
                .padding(.trailing, 10)
                .allowsHitTesting(false)
                .accessibilityHidden(true)
        }
    }

    // MARK: - Cabeçalho

    private var header: some View {
        GeometryReader { geometry in
            VStack(alignment: .leading, spacing: 6) {
                Text("PDF Split")  // Maiúsculas/minúsculas normal
                    .font(.system(size: CGFloat(titleFontSize), weight: .black, design: .default))
                    .tracking(1.5)
                    .foregroundColor(Color(red: 0.55, green: 0.42, blue: 0.14))  // BRONZE/OURO VELHO
                    .shadow(color: .black.opacity(0.5), radius: 1, x: 1, y: 1)

                Text("Powered by Max.1974")
                    .font(.system(size: CGFloat(subtitleFontSize), weight: .bold, design: .default))
                    .tracking(0.5)
                    .foregroundColor(Color(red: 0.55, green: 0.42, blue: 0.14))  // MESMO BRONZE
                    .shadow(color: .black.opacity(0.3), radius: 1, x: 0, y: 1)
            }
            .position(headerPosition)
            .gesture(
                debugMode ?
                DragGesture()
                    .onChanged { value in
                        headerPosition = value.location
                    }
                    .onEnded { value in
                        headerPosition = value.location
                        savedX = headerPosition.x  // Salva X
                        savedY = headerPosition.y  // Salva Y
                        print("Nova posição do header SALVA: x:\(Int(headerPosition.x)) y:\(Int(headerPosition.y))")
                    }
                : nil
            )
            // Indicador visual do modo debug
            .overlay(
                debugMode ?
                ZStack {
                    // Cruz para mostrar o ponto central
                    Path { path in
                        path.move(to: CGPoint(x: -10, y: 0))
                        path.addLine(to: CGPoint(x: 10, y: 0))
                        path.move(to: CGPoint(x: 0, y: -10))
                        path.addLine(to: CGPoint(x: 0, y: 10))
                    }
                    .stroke(Color.red, lineWidth: 1)
                    
                    // Caixa de coordenadas e controles de tamanho
                    VStack(spacing: 4) {
                        Text("x:\(Int(headerPosition.x)) y:\(Int(headerPosition.y))")
                            .font(.system(size: 10, design: .monospaced))
                        
                        HStack(spacing: 8) {
                            // Controles do título
                            Button("-") {
                                titleFontSize = max(16, titleFontSize - 2)
                            }
                            .buttonStyle(.plain)
                            .foregroundColor(.yellow)
                            
                            Text("T:\(Int(titleFontSize))")
                                .font(.system(size: 10, design: .monospaced))
                            
                            Button("+") {
                                titleFontSize = min(48, titleFontSize + 2)
                            }
                            .buttonStyle(.plain)
                            .foregroundColor(.yellow)
                            
                            Text("|")
                                .foregroundColor(.gray)
                            
                            // Controles do subtítulo
                            Button("-") {
                                subtitleFontSize = max(8, subtitleFontSize - 1)
                            }
                            .buttonStyle(.plain)
                            .foregroundColor(.yellow)
                            
                            Text("S:\(Int(subtitleFontSize))")
                                .font(.system(size: 10, design: .monospaced))
                            
                            Button("+") {
                                subtitleFontSize = min(20, subtitleFontSize + 1)
                            }
                            .buttonStyle(.plain)
                            .foregroundColor(.yellow)
                        }
                    }
                    .padding(4)
                    .background(Color.black.opacity(0.85))
                    .foregroundColor(.yellow)
                    .cornerRadius(4)
                    .offset(y: -45)
                }
                .position(headerPosition)
                : nil
            )
            .background(
                debugMode ?
                Rectangle()
                    .fill(Color.blue.opacity(0.1))
                    .border(Color.blue.opacity(0.3), width: 1)
                : nil
            )
        }
        .frame(height: 60)  // Define altura fixa para o header
    }

    // MARK: - Drop zone (sem borda pontilhada, ícone amarelo mantido)

    private func dropZone() -> some View {
        return ZStack {
            VStack(spacing: 12) {
                Image(systemName: "arrow.down.doc.fill")
                    .font(.system(size: 60, weight: .semibold))  // ÍCONE BEM MAIOR
                    .foregroundColor(.yellow)
                Text("Arraste seu PDF")
                    .font(.title3)  // TEXTO MAIOR TAMBÉM
                    .foregroundColor(.yellow)
                    .bold()
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .modifier(DropDestinationCompat(isTargeted: $isTargeted) { urls in
            enqueueAndStart(urls)
        })
    }

    // MARK: - Botões (duas colunas)

    private var twoColumnButtons: some View {
        HStack(spacing: columnsHSpacing) {
            Spacer()

            VStack(spacing: columnVSpacing) {
                fatButton(title: "Escolher PDF/Pasta… (⌘O)", systemImage: "doc.badge.plus", tint: Color(red: 1.0, green: 0.84, blue: 0.0), prominent: true) {
                    openPickerAndProcess()
                }
                .keyboardShortcut("o", modifiers: [.command])

                fatButton(title: "Abrir pasta principal (⇧⌘O)", systemImage: "folder.fill", tint: Color(red: 1.0, green: 0.84, blue: 0.0), prominent: true) {
                    openPrincipalDirectory()
                }
                .keyboardShortcut("o", modifiers: [.command, .shift])
            }

            VStack(spacing: columnVSpacing) {
                fatButton(title: "Abrir última saída (⇧⌘S)", systemImage: "folder", tint: Color(red: 1.0, green: 0.84, blue: 0.0), prominent: true) {
                    openOutDirectory()
                }
                .keyboardShortcut("s", modifiers: [.command, .shift])

                fatButton(title: "Deletar itens… (⌥⌘⌫)", systemImage: "trash.fill", tint: Color(red: 1.0, green: 0.84, blue: 0.0), prominent: true) {
                    deleteOriginFlow()
                }
                .keyboardShortcut(.delete, modifiers: [.command, .option])
            }

            Spacer()
        }
    }

    // Helper comum para TODOS os botões (mesma largura/altura)
    @ViewBuilder
    private func fatButton(title: String,
                           systemImage: String,
                           tint: Color,
                           prominent: Bool,
                           action: @escaping () -> Void) -> some View {
        if prominent {
            Button(action: action) {
                Label {
                    Text(title)
                        .lineLimit(1)
                        .fixedSize(horizontal: true, vertical: false)
                } icon: {
                    Image(systemName: systemImage)
                }
                .frame(width: buttonWidth)
                .padding(.horizontal, 6)
            }
            .buttonStyle(FilledButtonStyle(tint: tint))
        } else {
            Button(action: action) {
                Label {
                    Text(title)
                        .lineLimit(1)
                        .fixedSize(horizontal: true, vertical: false)
                } icon: {
                    Image(systemName: systemImage)
                }
                .frame(width: buttonWidth)
                .padding(.horizontal, 6)
            }
            .buttonStyle(OutlineButtonStyleCompat(tint: tint))
        }
    }

    // MARK: - Barra inferior

    private var bottomBar: some View {
        HStack(spacing: bottomBarSpacing) {
            Spacer()

            fatButton(title: "Copiar log (⌘C)", systemImage: "doc.on.doc", tint: Color(red: 1.0, green: 0.84, blue: 0.0), prominent: false) {
                copyLogToClipboard()
            }
            .keyboardShortcut("c", modifiers: [.command])

            fatButton(title: "Fechar (⌘Q)", systemImage: "xmark.circle.fill", tint: Color(red: 1.0, green: 0.84, blue: 0.0), prominent: false) {
                NSApplication.shared.terminate(nil)
            }
            .keyboardShortcut("q", modifiers: [.command])

            Spacer()
        }
    }

    // MARK: - Ações/diálogos

    private func copyLogToClipboard() {
        let logText = messages.joined(separator: "\n")
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(logText, forType: .string)
    }

    private func openPickerAndProcess() {
        let p = NSOpenPanel()
        p.title = "Escolher PDF(s) ou pasta(s) para processar"
        p.prompt = "Processar"
        p.canChooseFiles = true
        p.canChooseDirectories = true
        p.allowsMultipleSelection = true
        p.allowedContentTypes = [.pdf] // diretórios continuam permitidos
        if p.runModal() == .OK { enqueueAndStart(p.urls) }
    }

    private func openOutDirectory() {
        if let out = lastOutDir, FileManager.default.fileExists(atPath: out.path) {
            NSWorkspace.shared.open(out); return
        }
        // tenta achar a saída mais recente dentro da última principal
        if let principal = lastPrincipalDir,
           let latest = mostRecentBucket(in: principal, suffix: "Mandados Separados") {
            lastOutDir = latest
            NSWorkspace.shared.open(latest); return
        }
        // manual
        let p = NSOpenPanel()
        p.title = "Escolher a pasta de saída (NNN-Mandados Separados)"
        p.canChooseFiles = false
        p.canChooseDirectories = true
        if p.runModal() == .OK, let u = p.url {
            lastOutDir = u
            NSWorkspace.shared.open(u)
        }
    }

    private func openPrincipalDirectory() {
        if let principal = lastPrincipalDir, FileManager.default.fileExists(atPath: principal.path) {
            NSWorkspace.shared.open(principal); return
        }
        let p = NSOpenPanel()
        p.title = "Escolher a pasta \"Mandados a Separar\""
        p.canChooseFiles = false
        p.canChooseDirectories = true
        if p.runModal() == .OK, let u = p.url {
            lastPrincipalDir = u
            NSWorkspace.shared.open(u)
        }
    }

    private func deleteOriginFlow() {
        // por padrão abre na pasta principal, para você escolher o que quiser apagar
        let p = NSOpenPanel()
        p.title = "Selecione itens para DELETAR (sem lixeira)"
        p.prompt = "Deletar"
        p.canChooseFiles = true
        p.canChooseDirectories = true
        p.allowsMultipleSelection = true
        p.directoryURL = lastPrincipalDir
        if p.runModal() == .OK {
            for u in p.urls {
                do {
                    try FileManager.default.removeItem(at: u)
                    messages.append("🗑️ Deletado: \(u.path)")
                } catch {
                    messages.append("❌ Falha ao deletar \(u.lastPathComponent): \(error.localizedDescription)")
                }
            }
        }
    }

    // MARK: - Fila / execução

    private func enqueueAndStart(_ urls: [URL]) {
        queue.append(contentsOf: urls)
        if currentItem == nil { processNext() }
    }

    private func processNext() {
        guard !queue.isEmpty else {
            currentItem = nil
            isProcessing = false
            return
        }
        let item = queue.removeFirst()
        currentItem = item
        isProcessing = true
        runScriptOn(item)
    }

    private func runScriptOn(_ originalURL: URL) {
        guard let scriptURL = PythonRunner.bundledScriptURL() else {
            messages.append("❌ Script embutido não encontrado.")
            isProcessing = false
            processNext()
            return
        }

        let principal = principalRoot(for: originalURL)
        messages.append("🔎 Validando ambiente Python antes da separação…")

        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let runtimeMessage = try PythonRunner.prepareRuntime()
                let hasScopedAccess = originalURL.startAccessingSecurityScopedResource()
                defer {
                    if hasScopedAccess {
                        originalURL.stopAccessingSecurityScopedResource()
                    }
                }

                try FileManager.default.createDirectory(at: principal, withIntermediateDirectories: true)
                let index = nextGlobalIndex(inPrincipal: principal)

                let origemBucket = principal.appendingPathComponent(String(format: "%03d-PDFs de Origem", index), isDirectory: true)
                let saidaBucket  = principal.appendingPathComponent(String(format: "%03d-Mandados Separados", index), isDirectory: true)
                try FileManager.default.createDirectory(at: origemBucket, withIntermediateDirectories: true)
                try FileManager.default.createDirectory(at: saidaBucket, withIntermediateDirectories: true)

                guard let copied = copyToOriginBucket(originalURL, index: index, into: origemBucket) else {
                    throw CocoaError(.fileWriteUnknown)
                }

                let out = try PythonRunner.run(script: scriptURL, withTarget: copied, outputDir: saidaBucket)
                DispatchQueue.main.async {
                    self.lastPrincipalDir = principal
                    self.lastOutDir = saidaBucket
                    self.messages.append("✅ \(runtimeMessage)")
                    self.messages.append("📄 Cópia criada: \(copied.lastPathComponent)")
                    self.messages.append("▶️ Executando em (cópia): \(copied.lastPathComponent)")
                    self.messages.append("📁 Principal: \(principal.lastPathComponent)")
                    self.messages.append("📁 Origem: \(origemBucket.lastPathComponent)")
                    self.messages.append("📁 Saída:  \(saidaBucket.lastPathComponent)")
                    self.messages.append(contentsOf: out.split(separator: "\n").map(String.init))
                    self.messages.append("✅ Concluído: \(copied.lastPathComponent)")
                    self.isProcessing = false
                    NSWorkspace.shared.open(saidaBucket)
                    self.processNext()
                }
            } catch {
                DispatchQueue.main.async {
                    self.messages.append("❌ Erro: \(error.localizedDescription)")
                    self.messages.append("ℹ️ Nenhuma pasta numerada nova foi criada antes da validação do runtime.")
                    self.isProcessing = false
                    if FileManager.default.fileExists(atPath: principal.path) {
                        NSWorkspace.shared.open(principal)
                    }
                    self.processNext()
                }
            }
        }
    }

    // MARK: - Organização / utilitários

    /// retorna …/<dir do original>/Mandados a Separar
    private func principalRoot(for url: URL) -> URL {
        url.deletingLastPathComponent().appendingPathComponent("Mandados a Separar", isDirectory: true)
    }

    /// Varre subpastas da principal e retorna o próximo índice (olha tanto "NNN-PDFs de Origem" quanto "NNN-Mandados Separados")
    private func nextGlobalIndex(inPrincipal principal: URL) -> Int {
        let fm = FileManager.default
        var maxN = 0
        if let items = try? fm.contentsOfDirectory(at: principal, includingPropertiesForKeys: [.isDirectoryKey], options: [.skipsHiddenFiles]) {
            for u in items {
                guard (try? u.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) == true else { continue }
                if let n = leadingIndex(in: u.lastPathComponent) { maxN = max(maxN, n) }
            }
        }
        return maxN + 1
    }

    /// extrai NNN do início do nome
    private func leadingIndex(in name: String) -> Int? {
        if let r = name.range(of: #"^\d{3}"#, options: .regularExpression) {
            return Int(name[r])
        }
        return nil
    }

    /// Copia arquivo/pasta `src` para `destDir` com nome "NNN - <base>[.ext]". Retorna URL da cópia.
    private func copyToOriginBucket(_ src: URL, index: Int, into destDir: URL) -> URL? {
        let fm = FileManager.default
        let isDir = (try? src.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) ?? false
        let base = src.deletingPathExtension().lastPathComponent
        let ext  = src.pathExtension
        let name = ext.isEmpty ? String(format: "%03d - %@", index, base)
                               : String(format: "%03d - %@.%@", index, base, ext)
        var dest = destDir.appendingPathComponent(name, isDirectory: isDir)
        dest = uniqueDestination(dest, isDir: isDir)
        do {
            try fm.copyItem(at: src, to: dest)
            return dest
        } catch {
            return nil
        }
    }

    /// retorna a subpasta mais recente com certo sufixo (ex: "Mandados Separados")
    private func mostRecentBucket(in principal: URL, suffix: String) -> URL? {
        let fm = FileManager.default
        guard let items = try? fm.contentsOfDirectory(at: principal, includingPropertiesForKeys: [.isDirectoryKey], options: [.skipsHiddenFiles]) else { return nil }
        var best: (n: Int, url: URL)? = nil
        for u in items {
            guard (try? u.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) == true else { continue }
            let name = u.lastPathComponent
            guard name.contains(suffix), let n = leadingIndex(in: name) else { continue }
            if best == nil || n > best!.n { best = (n, u) }
        }
        return best?.url
    }

    private func uniqueDestination(_ url: URL, isDir: Bool) -> URL {
        let fm = FileManager.default
        if !fm.fileExists(atPath: url.path) { return url }
        let ext = url.pathExtension
        let base = url.deletingPathExtension().lastPathComponent
        let dir = url.deletingLastPathComponent()
        var n = 2
        while true {
            let name = ext.isEmpty ? "\(base) (\(n))" : "\(base) (\(n)).\(ext)"
            let cand = dir.appendingPathComponent(name, isDirectory: isDir)
            if !fm.fileExists(atPath: cand.path) { return cand }
            n += 1
        }
    }
}

// Compat: drop também funciona em macOS 12
private struct DropDestinationCompat: ViewModifier {
    @Binding var isTargeted: Bool
    var onDrop: ([URL]) -> Void

    private func decodeDroppedURL(from item: NSSecureCoding?) -> URL? {
        if let url = item as? URL {
            return url.isFileURL ? url : nil
        }

        if let nsurl = item as? NSURL {
            let url = nsurl as URL
            return url.isFileURL ? url : nil
        }

        if let data = item as? Data {
            if let nsurl = try? NSKeyedUnarchiver.unarchivedObject(ofClass: NSURL.self, from: data) {
                let url = nsurl as URL
                if url.isFileURL { return url }
            }

            if let text = String(data: data, encoding: .utf8) {
                let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
                if let url = URL(string: trimmed), url.isFileURL {
                    return url
                }
            }
        }

        if let text = item as? String {
            let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
            if let url = URL(string: trimmed), url.isFileURL {
                return url
            }
        }

        return nil
    }

    func body(content: Content) -> some View {
        if #available(macOS 13.0, *) {
            content.dropDestination(for: URL.self) { urls, _ in
                let valid = urls.filter { $0.isFileURL }
                if !valid.isEmpty {
                    onDrop(valid)
                }
                return !valid.isEmpty
            } isTargeted: { t in isTargeted = t }
        } else {
            content.onDrop(of: [UTType.fileURL.identifier], isTargeted: $isTargeted) { providers in
                var urls: [URL] = []; let g = DispatchGroup()
                for p in providers {
                    g.enter()
                    p.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
                        defer { g.leave() }
                        if let url = decodeDroppedURL(from: item) {
                            urls.append(url)
                        }
                    }
                }
                g.notify(queue: .main) { if !urls.isEmpty { onDrop(urls) } }
                return true
            }
        }
    }
}
