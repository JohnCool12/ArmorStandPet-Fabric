package limitless.enchantments;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.HexFormat;

public final class EnchantmentsPersistentState {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final SecureRandom RNG = new SecureRandom();

    private EnchantmentsPersistentState() {
    }

    public static void save(ServerLevel world, String name, JsonElement json) {
        try {
            MinecraftServer server = world.getServer();
            Path dir = worldDataDir(server);
            Files.createDirectories(dir);

            SecretKey key = loadOrCreateKey(keyDir(server));
            byte[] plaintext = GSON.toJson(json).getBytes(StandardCharsets.UTF_8);
            byte[] enc = Crypto.encryptAesGcm(key, plaintext, buildAAD(name));

            Path out = dir.resolve(safeFileName(name) + ".dat");
            Files.write(out, enc);
        }
        catch (IOException e) {
        }
        catch (GeneralSecurityException e) {
        }
    }

    public static JsonElement load(ServerLevel world, String name) {
        try {
            MinecraftServer server = world.getServer();
            Path dir = worldDataDir(server);
            Path in = dir.resolve(safeFileName(name) + ".dat");
            if (!Files.exists(in)) {
                LimitlessEnchantments.LOGGER.info(in + " doesn't exist? Probably initial boot.");
                return null;
            }

            SecretKey key = loadOrCreateKey(keyDir(server));
            byte[] enc = Files.readAllBytes(in);
            byte[] dec;
            boolean migratedLegacyFile = false;

            try {
                dec = Crypto.decryptAesGcm(key, enc, buildAAD(name));
            }
            catch (GeneralSecurityException globalFailure) {
                try {
                    dec = Crypto.decryptAesGcm(key, enc, buildLegacyAAD(world, name));
                    migratedLegacyFile = true;
                }
                catch (GeneralSecurityException legacyFailure) {
                    globalFailure.addSuppressed(legacyFailure);
                    throw globalFailure;
                }
            }

            if (migratedLegacyFile) {
                byte[] migrated = Crypto.encryptAesGcm(key, dec, buildAAD(name));
                Files.write(in, migrated);
                LimitlessEnchantments.LOGGER.info("Migrated Limitless Enchantments settings to dimension-independent storage authentication.");
            }

            return JsonParser.parseString(new String(dec, StandardCharsets.UTF_8));
        }
        catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        catch (GeneralSecurityException e) {
            throw new RuntimeException(e);
        }
    }

    public static boolean delete(ServerLevel world, String name) {
        try {
            Path dir = worldDataDir(world.getServer());
            Path in = dir.resolve(safeFileName(name) + ".dat");
            if (Files.exists(in)) {
                Files.delete(in);
                return true;
            }
            return false;
        }
        catch (IOException e) {
            return false;
        }
    }

    private static byte[] buildAAD(String name) {
        String aadStr = LimitlessEnchantments.MOD_ID + "|global|" + name;
        return aadStr.getBytes(StandardCharsets.UTF_8);
    }

    private static byte[] buildLegacyAAD(ServerLevel world, String name) {
        String dimId = safeFileName(world.toString());
        String aadStr = LimitlessEnchantments.MOD_ID + "|" + dimId + "|" + name;
        return aadStr.getBytes(StandardCharsets.UTF_8);
    }

    private static Path worldDataDir(MinecraftServer server) {
        Path root = server.getWorldPath(LevelResource.ROOT);
        return root.resolve("data");
    }

    private static Path keyDir(MinecraftServer server) {
        return server.getWorldPath(LevelResource.ROOT);
    }

    private static String safeFileName(String s) {
        String safe = s.replaceAll("[^a-zA-Z0-9-_]", "_");
        if (safe.isBlank())
            safe = "entry" + HexFormat.of().formatHex(random(4));
        return safe;
    }

    private static SecretKey loadOrCreateKey(Path dir) throws IOException, GeneralSecurityException {
        Path keyFile = dir.resolve("key.bin");
        if (Files.exists(keyFile)) {
            byte[] raw = Files.readAllBytes(keyFile);
            if (raw.length != 32)
                throw new GeneralSecurityException("Invalid key.bin length: " + raw.length);
            return new SecretKeySpec(raw, "AES");
        }
        KeyGenerator kg = KeyGenerator.getInstance("AES");
        kg.init(256, RNG);
        SecretKey key = kg.generateKey();
        byte[] raw = key.getEncoded();
        Files.createDirectories(dir);
        Files.write(keyFile, raw);
        return key;
    }

    private static byte[] random(int len) {
        byte[] b = new byte[len];
        RNG.nextBytes(b);
        return b;
    }

    private static final class Crypto {
        private static final int GCM_TAG_BITS = 128;

        static byte[] encryptAesGcm(SecretKey key, byte[] plaintext, byte[] aad) throws GeneralSecurityException {
            byte[] iv = random(12);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(GCM_TAG_BITS, iv));
            if (aad != null && aad.length > 0)
                cipher.updateAAD(aad);
            byte[] ct = cipher.doFinal(plaintext);
            byte[] out = new byte[1 + iv.length + ct.length];
            out[0] = 0x01;
            System.arraycopy(iv, 0, out, 1, iv.length);
            System.arraycopy(ct, 0, out, 1 + iv.length, ct.length);
            return out;
        }

        static byte[] decryptAesGcm(SecretKey key, byte[] packed, byte[] aad) throws GeneralSecurityException {
            if (packed.length < 1 + 12 + 16)
                throw new GeneralSecurityException("Ciphertext too short");
            byte ver = packed[0];
            if (ver != 0x01)
                throw new GeneralSecurityException("Unsupported ciphertext version: " + ver);
            byte[] iv = new byte[12];
            System.arraycopy(packed, 1, iv, 0, 12);
            byte[] ct = new byte[packed.length - 1 - 12];
            System.arraycopy(packed, 13, ct, 0, ct.length);

            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(GCM_TAG_BITS, iv));
            if (aad != null && aad.length > 0)
                cipher.updateAAD(aad);
            return cipher.doFinal(ct);
        }
    }
}
