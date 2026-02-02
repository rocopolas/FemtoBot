import subprocess
import shutil

class CronUtils:
    @staticmethod
    def get_crontab():
        """Returns the current crontab content as a list of lines."""
        try:
            result = subprocess.run(['crontab', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                # crontab might be empty/no crontab for user
                return []
            return result.stdout.strip().split('\n')
        except FileNotFoundError:
            return []

    @staticmethod
    def add_job(schedule: str, command: str) -> bool:
        """Adds a new job to the crontab."""
        current_jobs = CronUtils.get_crontab()
        new_job = f"{schedule} {command}"
        
        # Avoid duplicates
        if new_job in current_jobs:
            return True
            
        current_jobs.append(new_job)
        
        return CronUtils._write_crontab(current_jobs)

    @staticmethod
    def delete_job(substring: str) -> bool:
        """Deletes jobs that match the substring."""
        current_jobs = CronUtils.get_crontab()
        new_jobs = [job for job in current_jobs if substring not in job]
        
        if len(new_jobs) == len(current_jobs):
            # Nothing changed
            return False
            
        return CronUtils._write_crontab(new_jobs)

    @staticmethod
    def _write_crontab(jobs: list) -> bool:
        """Helper to write list of jobs to crontab."""
        new_content = "\n".join(jobs) + "\n"
        try:
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(input=new_content)
            if process.returncode != 0:
                print(f"Error saving crontab: {stderr}")
                return False
            return True
        except Exception as e:
            print(f"Exception saving crontab: {e}")
            return False

    @staticmethod
    def cleanup_old_jobs() -> int:
        """
        Removes one-time cron jobs that have already passed.
        Returns the number of jobs removed.
        """
        import re
        from datetime import datetime
        
        current_jobs = CronUtils.get_crontab()
        now = datetime.now()
        jobs_to_keep = []
        removed_count = 0
        
        for job in current_jobs:
            if not job.strip():
                continue
                
            # Check if it's a one-time job (has year check like: [ "$(date +\%Y)" = "2026" ])
            year_match = re.search(r'\[ "\$\(date \+\\%Y\)" = "(\d{4})" \]', job)
            
            if year_match:
                # This is a one-time job, parse the schedule
                parts = job.split()
                if len(parts) >= 5:
                    try:
                        minute = int(parts[0])
                        hour = int(parts[1])
                        day = int(parts[2])
                        month = int(parts[3])
                        year = int(year_match.group(1))
                        
                        job_time = datetime(year, month, day, hour, minute)
                        
                        if job_time < now:
                            # This job is in the past, don't keep it
                            removed_count += 1
                            print(f"[CLEANUP] Removing old cron: {job[:60]}...")
                            continue
                    except (ValueError, IndexError):
                        pass  # Can't parse, keep it
            
            jobs_to_keep.append(job)
        
        if removed_count > 0:
            CronUtils._write_crontab(jobs_to_keep)
        
        return removed_count
