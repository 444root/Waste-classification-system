import {
  BadRequestException,
  ConflictException,
  Injectable,
  Logger,
  UnauthorizedException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { JwtService } from '@nestjs/jwt';
import * as argon2 from 'argon2';
import { createHash, randomBytes, randomUUID } from 'node:crypto';
import { DatabaseService } from '../database/database.service';
import { ForgotPasswordDto } from './dto/forgot-password.dto';
import { LoginDto } from './dto/login.dto';
import { RegisterDto } from './dto/register.dto';
import { ResetPasswordDto } from './dto/reset-password.dto';

interface UserRow {
  id: string;
  email: string;
  name: string;
  password_hash: string;
  role: 'user' | 'admin';
  token_version: number;
  created_at: Date;
}

interface PasswordResetResult {
  user_id: string;
}

export interface PublicUser {
  id: string;
  email: string;
  name: string;
  role: 'user' | 'admin';
  createdAt: Date;
}

@Injectable()
export class AuthService {
  private readonly logger = new Logger(AuthService.name);
  private readonly adminEmails: Set<string>;

  constructor(
    private readonly db: DatabaseService,
    private readonly jwt: JwtService,
    private readonly config: ConfigService,
  ) {
    this.adminEmails = new Set(
      this.config
        .get<string>('ADMIN_EMAILS', '')
        .split(',')
        .map((email) => email.trim().toLowerCase())
        .filter(Boolean),
    );
  }

  async register(dto: RegisterDto) {
    const email = dto.email.trim().toLowerCase();
    const existing = await this.findUserByEmail(email);
    if (existing) throw new ConflictException('Email is already registered');

    const id = randomUUID();
    const passwordHash = await argon2.hash(dto.password, {
      type: argon2.argon2id,
    });
    const role = this.adminEmails.has(email) ? 'admin' : 'user';
    const result = await this.db.query<UserRow>(
      `INSERT INTO users (id, email, name, password_hash, role)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING id, email, name, password_hash, role, token_version, created_at`,
      [id, email, dto.name.trim(), passwordHash, role],
    );
    return this.createSession(result.rows[0]);
  }

  async login(dto: LoginDto) {
    let user = await this.findUserByEmail(dto.email.trim().toLowerCase());
    if (!user || !(await argon2.verify(user.password_hash, dto.password))) {
      throw new UnauthorizedException('Invalid email or password');
    }
    if (this.adminEmails.has(user.email) && user.role !== 'admin') {
      const promoted = await this.db.query<UserRow>(
        `UPDATE users SET role = 'admin'
         WHERE id = $1
         RETURNING id, email, name, password_hash, role, token_version, created_at`,
        [user.id],
      );
      user = promoted.rows[0];
    }
    return this.createSession(user);
  }

  async forgotPassword(dto: ForgotPasswordDto) {
    const message =
      'If an account exists for that email, a password reset link has been sent.';
    const user = await this.findUserByEmail(dto.email.trim().toLowerCase());
    if (!user) return { message };

    const token = randomBytes(32).toString('hex');
    const tokenHash = this.hashResetToken(token);
    const expiresAt = new Date(Date.now() + 30 * 60 * 1000);

    await this.db.query(
      `UPDATE password_reset_tokens
       SET used_at = NOW()
       WHERE user_id = $1 AND used_at IS NULL`,
      [user.id],
    );
    await this.db.query(
      `INSERT INTO password_reset_tokens
         (id, user_id, token_hash, expires_at)
       VALUES ($1, $2, $3, $4)`,
      [randomUUID(), user.id, tokenHash, expiresAt],
    );

    const frontendUrl = this.config
      .get<string>('FRONTEND_URL', 'http://localhost:3000')
      .replace(/\/$/, '');
    const resetUrl = `${frontendUrl}/reset-password?token=${token}`;
    await this.sendPasswordResetEmail(user.email, resetUrl);

    return {
      message,
      ...(this.config.get<string>('NODE_ENV', 'development') !== 'production'
        ? { resetUrl }
        : {}),
    };
  }

  async resetPassword(dto: ResetPasswordDto) {
    const passwordHash = await argon2.hash(dto.password, {
      type: argon2.argon2id,
    });
    const result = await this.db.query<PasswordResetResult>(
      `WITH claimed_token AS (
         UPDATE password_reset_tokens
         SET used_at = NOW()
         WHERE token_hash = $1
           AND used_at IS NULL
           AND expires_at > NOW()
         RETURNING user_id
       )
       UPDATE users
       SET password_hash = $2,
           token_version = token_version + 1
       WHERE id = (SELECT user_id FROM claimed_token)
       RETURNING id AS user_id`,
      [this.hashResetToken(dto.token), passwordHash],
    );

    const reset = result.rows[0];
    if (!reset) {
      throw new BadRequestException('Reset link is invalid or has expired');
    }

    await this.db.query(
      `UPDATE password_reset_tokens
       SET used_at = NOW()
       WHERE user_id = $1 AND used_at IS NULL`,
      [reset.user_id],
    );
    return { message: 'Password reset successfully. You can now sign in.' };
  }

  async findPublicUserForSession(
    id: string,
    tokenVersion: number,
  ): Promise<PublicUser | null> {
    const result = await this.db.query<UserRow>(
      `SELECT id, email, name, password_hash, role, token_version, created_at
       FROM users
       WHERE id = $1 AND token_version = $2
       LIMIT 1`,
      [id, tokenVersion],
    );
    return result.rows[0] ? this.toPublicUser(result.rows[0]) : null;
  }

  private async findUserByEmail(email: string): Promise<UserRow | null> {
    const result = await this.db.query<UserRow>(
      `SELECT id, email, name, password_hash, role, token_version, created_at
       FROM users WHERE email = $1 LIMIT 1`,
      [email],
    );
    return result.rows[0] ?? null;
  }

  private createSession(user: UserRow) {
    const publicUser = this.toPublicUser(user);
    return {
      accessToken: this.jwt.sign({ sub: user.id, ver: user.token_version }),
      user: publicUser,
    };
  }

  private hashResetToken(token: string) {
    return createHash('sha256').update(token).digest('hex');
  }

  private async sendPasswordResetEmail(email: string, resetUrl: string) {
    const apiKey = this.config.get<string>('MAILEROO_API_KEY');
    if (!apiKey) {
      this.logger.log(`Password reset link for ${email}: ${resetUrl}`);
      return;
    }

    const fromEmail = this.config.get<string>(
      'EMAIL_FROM',
      'no-reply@sortwise.local',
    );
    const fromName = this.config.get<string>('EMAIL_FROM_NAME', 'Sortwise');
    const form = new FormData();
    form.append('from', `${fromName} <${fromEmail}>`);
    form.append('to', email);
    form.append('subject', 'Reset your Sortwise password');
    form.append(
      'html',
      `<p>We received a request to reset your Sortwise password.</p><p><a href="${resetUrl}">Reset password</a></p><p>This link expires in 30 minutes. If you did not request this, you can ignore this email.</p>`,
    );
    form.append(
      'plain',
      `Reset your Sortwise password: ${resetUrl}\n\nThis link expires in 30 minutes.`,
    );

    try {
      const response = await fetch('https://smtp.maileroo.com/send', {
        method: 'POST',
        headers: { 'X-API-Key': apiKey },
        body: form,
      });
      if (!response.ok) {
        this.logger.error(`Maileroo password reset failed: HTTP ${response.status}`);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      this.logger.error(`Maileroo password reset failed: ${message}`);
    }
  }

  private toPublicUser(user: UserRow): PublicUser {
    return {
      id: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
      createdAt: user.created_at,
    };
  }
}
