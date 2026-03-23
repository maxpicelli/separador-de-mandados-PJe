import Foundation
import AppKit

enum DragDropService {
    static let baseFolderName = "Mandados Separados"

    /// Retorna ~/Documents/Mandados Separados (criando se não existir)
    static func ensureBaseFolder() throws -> URL {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let base = docs.appendingPathComponent(baseFolderName, isDirectory: true)
        if !FileManager.default.fileExists(atPath: base.path) {
            try FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        }
        return base
    }

    /// Copia um item (arquivo ou pasta) para dentro de Mandados Separados.
    /// Se já existir, cria "nome (2).ext", "nome (3).ext"...
    static func copyItemToBase(_ url: URL) throws -> URL {
        let base = try ensureBaseFolder()
        let dest = uniqueDestination(base.appendingPathComponent(url.lastPathComponent, isDirectory: url.hasDirectoryPath))
        try FileManager.default.copyItem(at: url, to: dest)
        return dest
    }

    /// Gera um destino único se já existir algo com o mesmo nome.
    private static func uniqueDestination(_ url: URL) -> URL {
        let fm = FileManager.default
        guard fm.fileExists(atPath: url.path) else { return url }

        let ext = url.pathExtension
        let baseName = url.deletingPathExtension().lastPathComponent
        let folder = url.deletingLastPathComponent()

        var n = 2
        while true {
            let candidateName = ext.isEmpty ? "\(baseName) (\(n))" : "\(baseName) (\(n)).\(ext)"
            let candidate = folder.appendingPathComponent(candidateName, isDirectory: url.hasDirectoryPath)
            if !fm.fileExists(atPath: candidate.path) {
                return candidate
            }
            n += 1
        }
    }

    /// Abre a pasta no Finder
    static func revealBaseFolder() {
        if let base = try? ensureBaseFolder() {
            NSWorkspace.shared.activateFileViewerSelecting([base])
        }
    }
}
